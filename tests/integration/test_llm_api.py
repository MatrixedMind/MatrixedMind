from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.adapters.memory.repository import (
    InMemoryTestAuditEventRepository,
    InMemoryTestAutomationWriteRepository,
    InMemoryTestPersonalAccessTokenRepository,
    InMemoryTestRecordRepository,
)
from app.auth.dependencies import hash_personal_access_token, personal_access_token_rate_limiter
from app.dependencies import (
    get_audit_event_repository,
    get_automation_write_repository,
    get_personal_access_token_repository,
    get_record_repository,
)
from app.domain.models import AuditEvent, PersonalAccessToken, Record
from app.main import app
from app.settings import settings

RAW_TOKEN = "test-personal-access-token"


class ToggleAuditEventRepository(InMemoryTestAuditEventRepository):
    fail = False

    def append(self, event: AuditEvent) -> AuditEvent:
        if self.fail:
            raise RuntimeError("injected audit failure")
        return super().append(event)


@pytest.fixture
def repos() -> tuple[
    InMemoryTestRecordRepository,
    InMemoryTestPersonalAccessTokenRepository,
    ToggleAuditEventRepository,
]:
    records = InMemoryTestRecordRepository()
    tokens = InMemoryTestPersonalAccessTokenRepository()
    audits = ToggleAuditEventRepository()
    tokens.save(
        PersonalAccessToken(
            id="token-1",
            name="ChatGPT",
            token_hash=hash_personal_access_token(RAW_TOKEN),
            scopes=frozenset({"records:read", "records:write"}),
            allowed_spaces=frozenset({"personal"}),
            owner_id="dev-user",
            actor_id="llm:chatgpt",
        )
    )
    return records, tokens, audits


@pytest.fixture
def client(
    repos: tuple[
        InMemoryTestRecordRepository,
        InMemoryTestPersonalAccessTokenRepository,
        ToggleAuditEventRepository,
    ],
) -> Iterator[TestClient]:
    records, tokens, audits = repos
    app.dependency_overrides[get_record_repository] = lambda: records
    app.dependency_overrides[get_personal_access_token_repository] = lambda: tokens
    app.dependency_overrides[get_audit_event_repository] = lambda: audits
    app.dependency_overrides[get_automation_write_repository] = lambda: (
        InMemoryTestAutomationWriteRepository(records, audits)
    )
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
        InMemoryTestRecordRepository,
        InMemoryTestPersonalAccessTokenRepository,
        ToggleAuditEventRepository,
    ],
) -> None:
    response = client.post("/api/llm/records/upsert", json=payload(), headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["visibility"] == "private"
    assert data["draft"] is True
    assert data["index_after"] is None
    assert data["created_by"] == "llm:chatgpt"
    record = repos[0].get_by_slug("dev-user", "personal", "from-chatgpt")
    assert record is not None
    assert record.revisions[0].author_id == "llm:chatgpt"
    assert repos[2].events[0].action == "record.created"

    update = client.post(
        "/api/llm/records/upsert",
        json={**payload(), "body_markdown": "# Updated"},
        headers=auth_headers(),
    )
    assert update.status_code == 200
    record = repos[0].get_by_slug("dev-user", "personal", "from-chatgpt")
    assert record is not None
    assert len(record.revisions) == 2
    assert repos[2].events[-1].action == "record.updated"


def test_llm_upsert_rolls_back_create_when_audit_fails(
    client: TestClient,
    repos: tuple[
        InMemoryTestRecordRepository,
        InMemoryTestPersonalAccessTokenRepository,
        ToggleAuditEventRepository,
    ],
) -> None:
    repos[2].fail = True

    with pytest.raises(RuntimeError, match="injected audit failure"):
        client.post("/api/llm/records/upsert", json=payload(), headers=auth_headers())

    assert repos[0].get_by_slug("dev-user", "personal", "from-chatgpt") is None
    assert repos[2].events == []


def test_llm_upsert_rolls_back_update_and_revision_when_audit_fails(
    client: TestClient,
    repos: tuple[
        InMemoryTestRecordRepository,
        InMemoryTestPersonalAccessTokenRepository,
        ToggleAuditEventRepository,
    ],
) -> None:
    created = client.post("/api/llm/records/upsert", json=payload(), headers=auth_headers())
    assert created.status_code == 200
    before = repos[0].get_by_slug("dev-user", "personal", "from-chatgpt")
    assert before is not None

    repos[2].fail = True
    with pytest.raises(RuntimeError, match="injected audit failure"):
        client.post(
            "/api/llm/records/upsert",
            json={**payload(), "body_markdown": "# Must roll back"},
            headers=auth_headers(),
        )

    after = repos[0].get_by_slug("dev-user", "personal", "from-chatgpt")
    assert after == before
    assert len(repos[2].events) == 1


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


def test_llm_cannot_access_another_owner_and_can_create_its_own_same_slug_record(
    client: TestClient,
    repos: tuple[
        InMemoryTestRecordRepository,
        InMemoryTestPersonalAccessTokenRepository,
        ToggleAuditEventRepository,
    ],
) -> None:
    repos[0].create(
        Record(
            space="personal",
            slug="other-owner",
            title="Other Owner",
            body_markdown="# Private",
            owner_id="other-user",
        )
    )

    assert (
        client.get("/api/llm/records/personal/other-owner", headers=auth_headers()).status_code
        == 404
    )
    assert client.get("/api/llm/records?space=personal", headers=auth_headers()).json() == []

    create_own_record = client.post(
        "/api/llm/records/upsert",
        json={**payload(), "slug": "other-owner"},
        headers=auth_headers(),
    )
    assert create_own_record.status_code == 200
    other_record = repos[0].get_by_slug("other-user", "personal", "other-owner")
    own_record = repos[0].get_by_slug("dev-user", "personal", "other-owner")
    assert other_record is not None and other_record.title == "Other Owner"
    assert own_record is not None and own_record.owner_id == "dev-user"


def test_llm_api_rejects_missing_invalid_and_revoked_personal_access_tokens(
    client: TestClient,
    repos: tuple[
        InMemoryTestRecordRepository,
        InMemoryTestPersonalAccessTokenRepository,
        ToggleAuditEventRepository,
    ],
) -> None:
    missing = client.get("/api/llm/records?space=personal")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Personal access token required"
    invalid = client.get("/api/llm/records?space=personal", headers=auth_headers("wrong"))
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "Invalid personal access token"
    repos[1].revoke("token-1")
    revoked = client.get("/api/llm/records?space=personal", headers=auth_headers())
    assert revoked.status_code == 401
    assert revoked.json()["detail"] == "Invalid personal access token"


def test_llm_api_enforces_personal_access_token_scope(
    client: TestClient,
    repos: tuple[
        InMemoryTestRecordRepository,
        InMemoryTestPersonalAccessTokenRepository,
        ToggleAuditEventRepository,
    ],
) -> None:
    token = repos[1].get_by_hash(hash_personal_access_token(RAW_TOKEN))
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
    assert (
        client.post(
            "/api/llm/records/upsert",
            content=b"{}",
            headers={**auth_headers(), "Content-Length": "21"},
        ).status_code
        == 413
    )

    monkeypatch.setattr(settings, "llm_request_body_limit_bytes", 65_536)
    monkeypatch.setattr(settings, "llm_rate_limit_requests", 1)
    personal_access_token_rate_limiter._requests.clear()
    assert client.get("/api/llm/records?space=personal", headers=auth_headers()).status_code == 200
    assert client.get("/api/llm/records?space=personal", headers=auth_headers()).status_code == 429
    personal_access_token_rate_limiter._requests.clear()


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
