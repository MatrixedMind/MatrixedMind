from fastapi.testclient import TestClient

from app.adapters.memory.repository import InMemoryRecordRepository
from app.dependencies import get_record_repository
from app.main import app

client = TestClient(app)

# Override dependency to use in-memory repository
test_repo = InMemoryRecordRepository()


def override_get_record_repository() -> InMemoryRecordRepository:
    return test_repo


app.dependency_overrides[get_record_repository] = override_get_record_repository


def test_create_and_get_record() -> None:
    # 1. Create a record
    payload = {
        "space": "test",
        "slug": "hello-world",
        "title": "Hello World",
        "body_markdown": "# Hello\nThis is a test.",
        "tags": ["test", "integration"],
    }
    response = client.post("/api/records/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "hello-world"
    assert data["id"] is not None

    # 2. Get the record
    response = client.get("/api/records/test/hello-world")
    assert response.status_code == 200
    assert response.json()["title"] == "Hello World"


def test_get_nonexistent_record() -> None:
    response = client.get("/api/records/test/not-found")
    assert response.status_code == 404


def test_view_record_html() -> None:
    # The record from previous test should exist in test_repo if it's the same instance
    response = client.get("/test/hello-world")
    assert response.status_code == 200
    assert "<h1>Hello World</h1>" in response.text
    assert "<h1>Hello</h1>" in response.text  # Rendered markdown
