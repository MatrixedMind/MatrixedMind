"""Safely validate that a Firestore MongoDB backup can be restored.

This command intentionally operates on one fixed marker in one dedicated
collection. It never prints the configured connection URI or stored document.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import parse_qs, urlparse

from pymongo import MongoClient
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    NetworkTimeout,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)

FIRESTORE_MONGO_URI_ENV = "FIRESTORE_MONGO_URI"
COLLECTION_NAME = "restore_validation"
MARKER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
VALID_MODES = frozenset({"seed", "verify-and-test", "cleanup"})
SOURCE_DATABASE = "matrixedmind-spike"
TARGET_DATABASE_PREFIX = "matrixedmind-dev-restore-validation-"
TARGET_DATABASE_PATTERN = re.compile(rf"{re.escape(TARGET_DATABASE_PREFIX)}[0-9]{{8}}-[0-9]{{4}}")
REQUIRED_URI_OPTIONS = {
    "loadBalanced": ["true"],
    "tls": ["true"],
    "retryWrites": ["false"],
    "authMechanism": ["MONGODB-OIDC"],
    "authMechanismProperties": ["ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE"],
}


class ProbeValidationError(ValueError):
    """Raised when input cannot safely identify the one probe record."""


class ProbeRuntimeError(RuntimeError):
    """Report only a fixed operation stage and sanitized driver category."""

    def __init__(self, stage: str, category: str) -> None:
        self.stage = stage
        self.category = category
        super().__init__(f"{stage}/{category}")


def classify_database_error(error: Exception) -> str:
    """Classify a database exception without rendering its potentially sensitive message."""
    if isinstance(error, ServerSelectionTimeoutError):
        return "server-selection-timeout"
    if isinstance(error, NetworkTimeout):
        return "network-timeout"
    if isinstance(error, ConfigurationError):
        return "configuration-error"
    if isinstance(error, OperationFailure):
        if error.code in {13, 18}:
            return "authorization-failure"
        return "operation-failure"
    if isinstance(error, ConnectionFailure):
        return "connection-failure"
    if isinstance(error, PyMongoError):
        return "driver-error"
    return "unexpected-error"


def run_database_step(stage: str, operation: Callable[[], Any]) -> Any:
    """Run one database operation and discard all exception text on failure."""
    try:
        return operation()
    except Exception as error:
        raise ProbeRuntimeError(stage, classify_database_error(error)) from None


def marker_payload(marker_id: str) -> dict[str, object]:
    """Return the fixed, non-sensitive payload used for restore validation."""
    return {
        "_id": marker_id,
        "purpose": "matrixedmind-restore-validation",
        "version": 1,
    }


def validate_marker_id(marker_id: str | None) -> str:
    if marker_id is None or not MARKER_PATTERN.fullmatch(marker_id):
        raise ProbeValidationError("a valid marker ID is required")
    return marker_id


def firestore_uri_and_database(mode: str) -> tuple[str, str]:
    uri = os.getenv(FIRESTORE_MONGO_URI_ENV)
    if not uri:
        raise ProbeValidationError(f"{FIRESTORE_MONGO_URI_ENV} is required")

    parsed = urlparse(uri)
    database = parsed.path.removeprefix("/")
    try:
        port = parsed.port
    except ValueError as error:
        raise ProbeValidationError(f"{FIRESTORE_MONGO_URI_ENV} is invalid") from error
    if (
        parsed.scheme != "mongodb"
        or parsed.hostname is None
        or not parsed.hostname.endswith(".firestore.goog")
        or port != 443
        or parsed.username is not None
        or parsed.password is not None
        or not database
        or "/" in database
        or parsed.params
        or parsed.fragment
        or parse_qs(parsed.query, keep_blank_values=True) != REQUIRED_URI_OPTIONS
    ):
        raise ProbeValidationError(f"{FIRESTORE_MONGO_URI_ENV} is invalid")
    if mode in {"seed", "cleanup"} and database != SOURCE_DATABASE:
        raise ProbeValidationError("seed and cleanup require the exact development source database")
    if mode == "verify-and-test" and not TARGET_DATABASE_PATTERN.fullmatch(database):
        raise ProbeValidationError("verification requires an isolated restore target database")
    return uri, database


def create_client(uri: str) -> MongoClient[dict[str, Any]]:
    return MongoClient(uri, serverSelectionTimeoutMS=10_000)


def run_firestore_tests() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/firestore", "-rs"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode


def run_restore_probe(
    mode: str,
    marker_id: str | None,
    *,
    client_factory: Callable[[str], Any] = create_client,
    pytest_runner: Callable[[], int] = run_firestore_tests,
) -> int:
    """Run one safe restore-probe mode and return the pytest exit code if run."""
    if mode not in VALID_MODES:
        raise ProbeValidationError("mode must be seed, verify-and-test, or cleanup")

    validated_marker_id = validate_marker_id(marker_id)
    uri, database_name = firestore_uri_and_database(mode)
    client = run_database_step("client-create", lambda: client_factory(uri))
    primary_error: Exception | None = None
    try:
        collection = client[database_name][COLLECTION_NAME]
        expected_payload = marker_payload(validated_marker_id)

        if mode == "seed":
            run_database_step(
                "marker-write",
                lambda: collection.replace_one(
                    {"_id": validated_marker_id}, expected_payload, upsert=True
                ),
            )
            print("restore validation marker seeded")
            return 0

        if mode == "cleanup":
            result = run_database_step(
                "marker-delete",
                lambda: collection.delete_one({"_id": validated_marker_id}),
            )
            deleted_count = result.deleted_count
            print(f"restore validation marker cleanup deleted: {deleted_count}")
            return 0

        document = run_database_step(
            "marker-read", lambda: collection.find_one({"_id": validated_marker_id})
        )
        if document != expected_payload:
            raise ProbeValidationError("restore validation marker is missing or does not match")
        run_database_step("database-ping", lambda: client.admin.command("ping"))
        if pytest_runner() != 0:
            raise ProbeRuntimeError("repository-contract", "test-failure")
        return 0
    except Exception as error:
        primary_error = error
        raise
    finally:
        try:
            client.close()
        except Exception as error:
            if primary_error is None:
                raise ProbeRuntimeError("client-close", classify_database_error(error)) from None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", help="seed, verify-and-test, or cleanup")
    parser.add_argument("--marker-id", required=True, help="non-secret restore marker ID")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run_restore_probe(args.mode, args.marker_id)
    except ProbeValidationError as error:
        print(f"restore probe failed: {error}", file=sys.stderr)
        return 2
    except ProbeRuntimeError as error:
        print(f"restore probe failed: {error}", file=sys.stderr)
        return 1
    except Exception:
        # Unexpected errors can also include connection details, so print only a fixed category.
        print("restore probe failed: unexpected-error", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
