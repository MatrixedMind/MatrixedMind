import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.openapi import HTTP_METHODS
from app.settings import settings

EXPECTED_OPERATIONS = {
    ("/api/llm/records/upsert", "post", "upsertPrivateDraftRecord"),
    ("/api/llm/records/{space}/{slug}", "get", "getPrivateDraftRecord"),
    ("/api/llm/records", "get", "listPrivateDraftRecords"),
}


def test_llm_openapi_exposes_only_safe_llm_operations() -> None:
    response = TestClient(app, base_url="https://matrixedmind.example").get("/openapi-llm.json")

    assert response.status_code == 200
    schema = response.json()
    operations = {
        (path, method, operation["operationId"])
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS and isinstance(operation, dict)
    }
    assert operations == EXPECTED_OPERATIONS
    assert schema["servers"] == [{"url": "https://matrixedmind.example"}]


def test_llm_openapi_advertises_https_behind_production_tls_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "llm_api_server_url", "https://matrixedmind.example")

    schema = TestClient(app, base_url="http://attacker.example").get("/openapi-llm.json").json()

    assert schema["servers"] == [{"url": "https://matrixedmind.example"}]


def test_llm_openapi_requires_bearer_auth_for_every_operation() -> None:
    schema = TestClient(app).get("/openapi-llm.json").json()

    assert schema["components"]["securitySchemes"] == {
        "PersonalAccessToken": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API key",
            "description": "Scoped MatrixedMind personal access token.",
        }
    }
    for path_item in schema["paths"].values():
        for method, operation in path_item.items():
            if method in HTTP_METHODS and isinstance(operation, dict):
                assert operation["security"] == [{"PersonalAccessToken": []}]


def test_llm_openapi_request_schema_forbids_privileged_fields() -> None:
    schema = TestClient(app).get("/openapi-llm.json").json()
    upsert_schema = schema["components"]["schemas"]["LlmRecordUpsert"]

    assert upsert_schema["additionalProperties"] is False
    assert set(upsert_schema["properties"]) == {
        "space",
        "slug",
        "title",
        "body_markdown",
        "parent_id",
        "path",
        "tags",
    }
    assert not {
        "visibility",
        "draft",
        "index_after",
        "sharing_policy",
        "auth_settings",
        "publish",
        "delete",
        "admin_action",
        "bulk_import",
    } & set(upsert_schema["properties"])
