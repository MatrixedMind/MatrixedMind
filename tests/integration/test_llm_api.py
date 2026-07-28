from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.adapters.memory.repository import (
    InMemoryAuditEventRepository,
    InMemoryLlmTokenRepository,
    InMemoryRecordRepository,
)
from app.auth.dependencies import hash_llm_token, llm_rate_limiter
from app.dependencies import (
    get_audit_event_repository,
    get_llm_token_repository,
    get_record_repository,
)
from app.domain.models import LlmApiToken
from app.main import app
from app.settings import settings

RAW_TOKEN = "test-llm-token"


@pytest.fixture
def repos() -> tuple[
    InMemoryRecordRepository,
    InMemoryLlmTokenRepository,
    InMemoryAuditEventRepository,
]:
    records = InMemoryRecordRepository()
    tokens = InMemoryLlmTokenRepository()
    audits = InMemoryAuditEventRepository()
    tokens.save(
        LlmApiToken(
            id="token-1",
            name="ChatGPT",
            token_hash=hash_llm_token(RAW_TOKEN),
            scopes=frozenset({"records:read", "records:write"}),
            allowed_spaces=frozenset({"personal"}),
        )
    )
    return records, tokens, audits


@pytest.fixture
def client(
    repos: tuple[
        InMemoryRecordRepository,
        InMemoryLlmTokenRepository,
        InMemoryAuditEventRepository,
    ],
) -> Iterator[TestClient]:
    records, tokens, audits = repos
    app.dependency_overrides[get_record_repository] = lambda: records
    app.dependency_overrides[get_llm_token_repository] = lambda: tokens
    app.dependency_overrides[get_audit_event_repository] = lambda: audits
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def auth_headers(token: str = RAW_TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def payload() -> dict[str, object]:
    return {
        "space": "personal",
        "slug": "from-chatgpt",
        "title": "From ChatGPT",
        "body_markdown": "# Private note",
        "tags": ["chatgpt"],
    }


def test_llm_upsert_defaults_private_and_creates_revision_and_audit(
    client: TestClient,
    repos: tuple[
        InMemoryRecordRepository,
        InMemoryLlmTokenRepository,
        InMemoryAuditEventRepository,
    ],
) -> None:
    response = client.post("/api/llm/records/upsert", json=payload(), headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["visibility"] == "private"
    assert data["draft"] is True
    assert data["index_after"] is None
    assert data["created_by"] == "llm:chatgpt"
    record = repos[0].get_by_slug("personal", "from-chatgpt")
    assert record is not None
    assert record.revisions[0].author_id == "llm:chatgpt"
    assert repos[2].events[0].action == "record.created"

    update = client.post(
        "/api/llm/records/upsert",
        json={**payload(), "body_markdown": "# Updated"},
        headers=auth_headers(),
    )
    assert update.status_code == 200
    record = repos[0].get_by_slug("personal", "from-chatgpt")
    assert record is not None
    assert len(record.revisions) == 2
    assert repos[2].events[-1].action == "record.updated"


def test_llm_read_list_and_space_scope(client: TestClient) -> None:
    client.post("/api/llm/records/upsert", json=payload(), headers=auth_headers())
    assert (
        client.get("/api/llm/records/personal/from-chatgpt", headers=auth_headers()).status_code
        == 200
    )
    listed = client.get("/api/llm/records?space=personal", headers=auth_headers())
    assert [record["slug"] for record in listed.json()] == ["from-chatgpt"]
    assert client.get("/api/llm/records?space=other", headers=auth_headers()).status_code == 403
    assert (
        client.post(
            "/api/llm/records/upsert",
            json={**payload(), "space": "other"},
            headers=auth_headers(),
        ).status_code
        == 403
    )


def test_llm_rejects_missing_invalid_and_revoked_tokens(
    client: TestClient,
    repos: tuple[
        InMemoryRecordRepository,
        InMemoryLlmTokenRepository,
        InMemoryAuditEventRepository,
    ],
) -> None:
    assert client.get("/api/llm/records?space=personal").status_code == 401
    assert (
        client.get("/api/llm/records?space=personal", headers=auth_headers("wrong")).status_code
        == 401
    )
    repos[1].revoke("token-1")
    assert client.get("/api/llm/records?space=personal", headers=auth_headers()).status_code == 401


def test_llm_enforces_token_scope(
    client: TestClient,
    repos: tuple[
        InMemoryRecordRepository,
        InMemoryLlmTokenRepository,
        InMemoryAuditEventRepository,
    ],
) -> None:
    token = repos[1].get_by_hash(hash_llm_token(RAW_TOKEN))
    assert token is not None
    repos[1].save(token.model_copy(update={"scopes": frozenset({"records:read"})}))
    response = client.post("/api/llm/records/upsert", json=payload(), headers=auth_headers())
    assert response.status_code == 403


def test_llm_enforces_body_size_and_rate_limits(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_request_body_limit_bytes", 20)
    assert (
        client.post("/api/llm/records/upsert", json=payload(), headers=auth_headers()).status_code
        == 413
    )

    monkeypatch.setattr(settings, "llm_request_body_limit_bytes", 65_536)
    monkeypatch.setattr(settings, "llm_rate_limit_requests", 1)
    llm_rate_limiter._requests.clear()
    assert client.get("/api/llm/records?space=personal", headers=auth_headers()).status_code == 200
    assert client.get("/api/llm/records?space=personal", headers=auth_headers()).status_code == 429
    llm_rate_limiter._requests.clear()


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "visibility",
        "index_after",
        "sharing_policy",
        "auth_settings",
        "publish",
        "delete",
        "admin_action",
        "bulk_import",
    ],
)
def test_llm_rejects_forbidden_capabilities(
    client: TestClient,
    forbidden_field: str,
) -> None:
    response = client.post(
        "/api/llm/records/upsert",
        json={**payload(), forbidden_field: True},
        headers=auth_headers(),
    )
    assert response.status_code == 422


def test_llm_exposes_no_destructive_or_admin_routes(client: TestClient) -> None:
    assert (
        client.delete("/api/llm/records/personal/from-chatgpt", headers=auth_headers()).status_code
        == 405
    )
    assert client.post("/api/llm/admin", json={}, headers=auth_headers()).status_code == 404
