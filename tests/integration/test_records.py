from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.adapters.memory.repository import InMemoryRecordRepository
from app.dependencies import get_record_repository
from app.main import app


@pytest.fixture
def repo() -> InMemoryRecordRepository:
    return InMemoryRecordRepository()


@pytest.fixture
def client(repo: InMemoryRecordRepository) -> Iterator[TestClient]:
    app.dependency_overrides[get_record_repository] = lambda: repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def record_payload(slug: str = "hello-world") -> dict[str, object]:
    return {
        "space": "test",
        "slug": slug,
        "title": "Hello World",
        "body_markdown": "# Hello\nThis is a test.",
        "tags": ["test", "integration"],
    }


def test_create_and_get_record(client: TestClient) -> None:
    response = client.post("/api/records/", json=record_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["space"] == "test"
    assert data["slug"] == "hello-world"
    assert data["parent_id"] is None
    assert data["path"] is None
    assert data["tags"] == ["test", "integration"]

    response = client.get("/api/records/test/hello-world")

    assert response.status_code == 200
    assert response.json()["title"] == "Hello World"


def test_list_records_by_space_and_parent(client: TestClient) -> None:
    root_response = client.post("/api/records/", json=record_payload("root"))
    root_id = root_response.json()["id"]
    child_payload = {
        **record_payload("child"),
        "parent_id": root_id,
        "title": "Child",
        "body_markdown": "# Child",
    }
    client.post("/api/records/", json=child_payload)
    client.post("/api/records/", json={**record_payload("other"), "space": "other"})

    root_list = client.get("/api/records/test")
    child_list = client.get("/api/records/test", params={"parent_id": root_id})

    assert root_list.status_code == 200
    assert [record["slug"] for record in root_list.json()] == ["root"]
    assert child_list.status_code == 200
    assert [record["slug"] for record in child_list.json()] == ["child"]


def test_update_record(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.put(
        "/api/records/test/hello-world",
        json={
            "slug": "renamed-record",
            "title": "Renamed Record",
            "body_markdown": "# Renamed",
            "tags": ["updated"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "renamed-record"
    assert data["title"] == "Renamed Record"
    assert data["body_markdown"] == "# Renamed"
    assert data["tags"] == ["updated"]

    assert client.get("/api/records/test/hello-world").status_code == 404
    assert client.get("/api/records/test/renamed-record").status_code == 200


def test_create_duplicate_record_returns_400(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.post("/api/records/", json=record_payload())

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Record with slug 'hello-world' already exists in space 'test'"
    )


def test_update_duplicate_record_returns_400(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload("first"))
    client.post("/api/records/", json=record_payload("second"))

    response = client.put("/api/records/test/first", json={"slug": "second"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Record with slug 'second' already exists in space 'test'"


def test_get_nonexistent_record_returns_404(client: TestClient) -> None:
    response = client.get("/api/records/test/not-found")

    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        ({**record_payload(), "slug": "Hello"}, "slug"),
        ({**record_payload(), "title": "   "}, "title"),
        ({**record_payload(), "body_markdown": "\x00"}, "Markdown body"),
        ({**record_payload(), "tags": ["bad tag"]}, "tags"),
    ],
)
def test_create_invalid_payload_returns_validation_error(
    client: TestClient,
    payload: dict[str, object],
    expected_error: str,
) -> None:
    response = client.post("/api/records/", json=payload)

    assert response.status_code == 422
    assert expected_error in response.text


def test_update_empty_payload_returns_validation_error(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.put("/api/records/test/hello-world", json={})

    assert response.status_code == 422
    assert "update payload must include at least one field" in response.text


@pytest.mark.parametrize("field_name", ["space", "slug", "title", "body_markdown"])
def test_update_non_nullable_field_with_null_returns_validation_error(
    client: TestClient,
    field_name: str,
) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.put("/api/records/test/hello-world", json={field_name: None})

    assert response.status_code == 422
    assert f"{field_name} cannot be null" in response.text


def test_update_nullable_fields_with_null_succeeds(client: TestClient) -> None:
    create_response = client.post(
        "/api/records/",
        json={**record_payload(), "parent_id": "root-id"},
    )
    assert create_response.status_code == 201

    response = client.put(
        "/api/records/test/hello-world",
        json={"parent_id": None, "path": None, "tags": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["parent_id"] is None
    assert data["path"] is None
    assert data["tags"] == ["test", "integration"]


def test_index_html_returns_200_and_lists_default_records(client: TestClient) -> None:
    client.post("/api/records/", json={**record_payload(), "space": "default"})

    response = client.get("/")

    assert response.status_code == 200
    assert "<title>MatrixedMind</title>" in response.text
    assert '<a href="/">MatrixedMind</a>' in response.text
    assert '<a href="/default/hello-world">Hello World</a>' in response.text


def test_index_html_returns_200_without_records(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "No pages yet." in response.text


def test_view_record_html(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.get("/test/hello-world")

    assert response.status_code == 200
    assert "<title>Hello World</title>" in response.text
    assert '<a href="/">MatrixedMind</a>' in response.text
    assert "<h1>Hello World</h1>" in response.text
    assert "<h1>Hello</h1>" in response.text


def test_view_record_html_sanitizes_unsafe_link_scheme(client: TestClient) -> None:
    client.post(
        "/api/records/",
        json={
            **record_payload("unsafe-link"),
            "body_markdown": '<a href="javascript:alert(1)">click</a>',
        },
    )

    response = client.get("/test/unsafe-link")

    assert response.status_code == 200
    assert '<a href="javascript:alert(1)">' not in response.text
    assert '<a rel="noopener noreferrer">click</a>' in response.text


def test_view_record_html_sanitizes_raw_html_in_markdown(client: TestClient) -> None:
    client.post(
        "/api/records/",
        json={
            **record_payload("unsafe-html"),
            "body_markdown": '<img src="x" onerror="alert(1)"><script>alert(1)</script>safe',
        },
    )

    response = client.get("/test/unsafe-html")

    assert response.status_code == 200
    assert "<img" not in response.text
    assert "<script" not in response.text
    assert "onerror=" not in response.text
    assert "safe" in response.text
