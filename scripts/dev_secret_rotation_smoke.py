"""Run a non-production Cloud Run smoke check for a dev LLM-token rotation."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from pymongo import MongoClient

from app.adapters.mongo.security import MongoLlmTokenRepository
from app.auth.dependencies import hash_llm_token, issue_llm_token
from app.domain.models import LlmApiToken

FIRESTORE_MONGO_URI_ENV = "FIRESTORE_MONGO_URI"
DEV_SERVICE_URL_ENV = "DEV_SERVICE_URL"
METADATA_IDENTITY_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
)
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}")
SMOKE_SPACE = "closeout-smoke"
SOURCE_DATABASE = "matrixedmind-spike"
REQUIRED_URI_OPTIONS = {
    "loadBalanced": ["true"],
    "tls": ["true"],
    "retryWrites": ["false"],
    "authMechanism": ["MONGODB-OIDC"],
    "authMechanismProperties": ["ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE"],
}
DEV_SERVICE_HOST_PATTERN = re.compile(r"matrixedmind-dev-[0-9]+\.us-west1\.run\.app")
UNIQUE_SUFFIX_PATTERN = re.compile(r"[0-9a-f]{16}")


class SmokeValidationError(ValueError):
    """Raised when a smoke harness input is unsafe or incomplete."""


class SmokeCheckError(RuntimeError):
    """Raised when a named smoke check did not receive its expected status."""

    def __init__(self, check: str):
        self.check = check
        super().__init__(check)


def validate_run_id(run_id: str | None) -> str:
    if run_id is None or not RUN_ID_PATTERN.fullmatch(run_id):
        raise SmokeValidationError("a valid non-secret run ID is required")
    return run_id


def firestore_uri_and_database() -> tuple[str, str]:
    uri = os.getenv(FIRESTORE_MONGO_URI_ENV)
    if not uri:
        raise SmokeValidationError(f"{FIRESTORE_MONGO_URI_ENV} is required")
    parsed = urlparse(uri)
    database = parsed.path.removeprefix("/")
    try:
        port = parsed.port
    except ValueError as error:
        raise SmokeValidationError(f"{FIRESTORE_MONGO_URI_ENV} is invalid") from error
    if (
        parsed.scheme != "mongodb"
        or parsed.hostname is None
        or not parsed.hostname.endswith(".firestore.goog")
        or port != 443
        or parsed.username is not None
        or parsed.password is not None
        or database != SOURCE_DATABASE
        or "/" in database
        or parsed.params
        or parsed.fragment
        or parse_qs(parsed.query, keep_blank_values=True) != REQUIRED_URI_OPTIONS
    ):
        raise SmokeValidationError(f"{FIRESTORE_MONGO_URI_ENV} is invalid")
    return uri, database


def dev_service_url() -> str:
    value = os.getenv(DEV_SERVICE_URL_ENV)
    if not value:
        raise SmokeValidationError(f"{DEV_SERVICE_URL_ENV} is required")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or not DEV_SERVICE_HOST_PATTERN.fullmatch(parsed.hostname)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise SmokeValidationError(f"{DEV_SERVICE_URL_ENV} must be a canonical Cloud Run URL")
    return value.rstrip("/")


def create_mongo_client(uri: str) -> MongoClient[dict[str, Any]]:
    return MongoClient(uri, serverSelectionTimeoutMS=10_000)


def create_http_client() -> httpx.Client:
    return httpx.Client(timeout=10.0, trust_env=False)


def expect_status(response: Any, expected: int, check: str) -> None:
    if response.status_code != expected:
        raise SmokeCheckError(check)
    print(f"PASS {check}")


def metadata_identity_token(http_client: Any, audience: str) -> str:
    response = http_client.get(
        METADATA_IDENTITY_URL,
        params={"audience": audience},
        headers={"Metadata-Flavor": "Google"},
    )
    expect_status(response, 200, "metadata-id-token")
    token = str(response.text).strip()
    if not token:
        raise SmokeCheckError("metadata-id-token")
    return token


def smoke_token(run_id: str, raw_token: str, unique_suffix: str) -> LlmApiToken:
    if not UNIQUE_SUFFIX_PATTERN.fullmatch(unique_suffix):
        raise SmokeValidationError("generated token suffix is invalid")
    return LlmApiToken(
        id=f"closeout-smoke-{run_id}-{unique_suffix}",
        name=f"nonproduction-closeout-smoke-{run_id}-{unique_suffix}",
        token_hash=hash_llm_token(raw_token),
        scopes=frozenset({"records:read"}),
        allowed_spaces=frozenset({SMOKE_SPACE}),
        owner_id=f"nonproduction-smoke-owner-{run_id}",
        actor_id=f"nonproduction-smoke-actor-{run_id}",
    )


def run_smoke(
    run_id: str | None,
    *,
    mongo_client_factory: Callable[[str], Any] = create_mongo_client,
    http_client_factory: Callable[[], Any] = create_http_client,
    raw_token_factory: Callable[[], str] = issue_llm_token,
    unique_suffix_factory: Callable[[], str] = lambda: secrets.token_hex(8),
) -> int:
    """Run the bounded smoke test and return zero only after revocation is proven."""
    validated_run_id = validate_run_id(run_id)
    mongo_uri, database_name = firestore_uri_and_database()
    service_url = dev_service_url()
    mongo_client = mongo_client_factory(mongo_uri)
    http_client = http_client_factory()
    token: LlmApiToken | None = None
    token_repository: Any = None
    token_saved = False
    try:
        database = mongo_client[database_name]
        token_repository = MongoLlmTokenRepository(database, ensure_indexes=False)
        raw_token = raw_token_factory()
        token = smoke_token(validated_run_id, raw_token, unique_suffix_factory())
        if database.llm_api_tokens.find_one({"_id": token.id}, {"_id": 1}) is not None:
            raise SmokeValidationError("generated token ID already exists")
        token_repository.save(token)
        token_saved = True
        print("PASS llm-token-saved")

        identity_token = metadata_identity_token(http_client, service_url)
        platform_headers = {"X-Serverless-Authorization": f"Bearer {identity_token}"}
        headers = {
            "Authorization": f"Bearer {raw_token}",
            **platform_headers,
        }
        expect_status(
            http_client.get(f"{service_url}/health", headers=platform_headers), 200, "health"
        )
        expect_status(
            http_client.get(f"{service_url}/ready", headers=platform_headers), 200, "ready"
        )
        records_url = f"{service_url}/api/llm/records"
        expect_status(
            http_client.get(records_url, params={"space": SMOKE_SPACE}, headers=headers),
            200,
            "llm-records",
        )

        token_repository.revoke(token.id)
        print("PASS llm-token-revoked")
        expect_status(
            http_client.get(records_url, params={"space": SMOKE_SPACE}, headers=headers),
            401,
            "llm-token-rejected",
        )
        return 0
    finally:
        if token_saved and token is not None and token_repository is not None:
            # Repeat after the rejection check; this remains an exact-ID revoke.
            token_repository.revoke(token.id)
        http_client.close()
        mongo_client.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="non-secret run identifier")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run_smoke(args.run_id)
    except SmokeValidationError:
        print("FAIL validation", file=sys.stderr)
        return 2
    except SmokeCheckError as error:
        print(f"FAIL {error.check}", file=sys.stderr)
        return 1
    except Exception:
        # Connection and driver exceptions can contain credentials or endpoint details.
        print("FAIL smoke", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
