from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.adapters.memory.auth import InMemoryOwnerAuthRepository
from app.adapters.memory.repository import InMemoryRecordRepository
from app.auth.dependencies import get_owner_auth_repository
from app.dependencies import get_record_repository
from app.domain.models import Record
from app.main import app
from app.settings import settings


@pytest.fixture
def repo() -> InMemoryRecordRepository:
    return InMemoryRecordRepository()


@pytest.fixture
def client(repo: InMemoryRecordRepository) -> Iterator[TestClient]:
    app.dependency_overrides[get_record_repository] = lambda: repo
    app.dependency_overrides[get_owner_auth_repository] = InMemoryOwnerAuthRepository
    original_app_env = settings.app_env
    original_auth_mode = settings.auth_mode
    settings.app_env = "test"
    settings.auth_mode = "test"
    try:
        yield TestClient(app, headers={"X-Test-User-Id": "owner"})
    finally:
        settings.app_env = original_app_env
        settings.auth_mode = original_auth_mode
        app.dependency_overrides.clear()


def record_payload(slug: str = "hello-world") -> dict[str, object]:
    return {
        "space": "test",
        "slug": slug,
        "title": "Hello World",
        "body_markdown": "# Hello\nThis is a test.",
        "tags": ["test", "integration"],
    }


def test_protected_routes_require_identity_outside_dev_mode(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unauthenticated = TestClient(app)
    assert unauthenticated.get("/", follow_redirects=False).status_code == 303
    assert unauthenticated.post("/api/records/", json=record_payload()).status_code == 401
    assert client.get("/", headers={"X-Test-User-Id": "owner"}).status_code == 200


def test_source_offer_is_public_without_exposing_protected_content(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "auth_mode", "test")

    response = client.get("/source")

    assert response.status_code == 200
    assert '<meta name="robots" content="noindex,nofollow,noarchive">' in response.text
    assert "GNU Affero General Public License v3.0" in response.text
    assert (
        '<a href="https://github.com/MatrixedMind/MatrixedMind">'
        "View the corresponding source code</a>"
    ) in response.text
    assert "No pages yet" not in response.text


def test_read_and_list_filter_private_records_owned_by_another_user(
    client: TestClient,
    repo: InMemoryRecordRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo.create(
        Record(
            space="test",
            slug="someone-elses-private-record",
            title="Private",
            body_markdown="# Private",
            owner_id="another-user",
        )
    )
    monkeypatch.setattr(settings, "auth_mode", "test")
    headers = {"X-Test-User-Id": "owner"}
    assert (
        client.get("/api/records/test/someone-elses-private-record", headers=headers).status_code
        == 404
    )
    assert client.get("/api/records/test", headers=headers).json() == []


def test_owners_can_reuse_space_and_slug_without_cross_owner_updates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "auth_mode", "test")
    owner_headers = {"X-Test-User-Id": "owner"}
    other_headers = {"X-Test-User-Id": "other-owner"}

    assert (
        client.post("/api/records/", json=record_payload(), headers=owner_headers).status_code
        == 201
    )
    assert (
        client.post("/api/records/", json=record_payload(), headers=other_headers).status_code
        == 201
    )
    assert (
        client.put(
            "/api/records/test/hello-world",
            json={"title": "Other Owner Update"},
            headers=other_headers,
        ).status_code
        == 200
    )

    owner = client.get("/api/records/test/hello-world", headers=owner_headers)
    other = client.get("/api/records/test/hello-world", headers=other_headers)
    assert owner.json()["title"] == "Hello World"
    assert other.json()["title"] == "Other Owner Update"


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
    assert data["visibility"] == "private"
    assert data["index_after"] is None

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


def test_public_create_without_index_after_sets_index_delay(client: TestClient) -> None:
    response = client.post("/api/records/", json={**record_payload(), "visibility": "public"})

    assert response.status_code == 201
    data = response.json()
    assert data["visibility"] == "public"
    assert datetime.fromisoformat(data["index_after"]) > datetime.now(UTC)


def test_private_to_public_update_sets_index_delay(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.put("/api/records/test/hello-world", json={"visibility": "public"})

    assert response.status_code == 200
    data = response.json()
    assert data["visibility"] == "public"
    assert datetime.fromisoformat(data["index_after"]) > datetime.now(UTC)


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
    assert '<meta name="robots" content="noindex,nofollow,noarchive">' in response.text
    assert '<a class="brand" href="/">MatrixedMind</a>' in response.text
    assert '<a class="button" href="/records/new">New Page</a>' in response.text
    assert '<a href="/default/hello-world">Hello World</a>' in response.text


def test_index_html_returns_200_without_records(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "No pages yet." in response.text


def test_new_record_editor_html_returns_200(client: TestClient) -> None:
    response = client.get("/records/new")

    assert response.status_code == 200
    assert "<title>New Page</title>" in response.text
    assert '<meta name="robots" content="noindex,nofollow,noarchive">' in response.text
    assert '<form method="post" action="/records/new">' in response.text
    assert 'name="space"' in response.text
    assert 'name="slug"' in response.text
    assert 'name="title"' in response.text
    assert 'name="body_markdown"' in response.text
    assert '<a href="/">Cancel</a>' in response.text


def test_create_record_from_editor_redirects_to_detail(client: TestClient) -> None:
    response = client.post(
        "/records/new",
        data={
            "space": "default",
            "slug": "from-form",
            "title": "From Form",
            "body_markdown": "# From Form",
            "tags": "form, web",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/default/from-form"

    detail = client.get("/default/from-form")
    assert detail.status_code == 200
    assert "<h1>From Form</h1>" in detail.text
    assert client.get("/api/records/default/from-form").json()["tags"] == ["form", "web"]


def test_create_record_from_editor_returns_400_for_invalid_payload(client: TestClient) -> None:
    response = client.post(
        "/records/new",
        data={
            "space": "default",
            "slug": "Bad Slug",
            "title": "From Form",
            "body_markdown": "# From Form",
            "tags": "form",
        },
    )

    assert response.status_code == 400
    assert 'role="alert"' in response.text
    assert "slug" in response.text
    assert 'value="Bad Slug"' in response.text


def test_create_record_from_editor_returns_400_for_duplicate_slug(client: TestClient) -> None:
    client.post("/api/records/", json={**record_payload(), "space": "default"})

    response = client.post(
        "/records/new",
        data={
            "space": "default",
            "slug": "hello-world",
            "title": "Duplicate",
            "body_markdown": "# Duplicate",
            "tags": "",
        },
    )

    assert response.status_code == 400
    assert (
        "Record with slug &#39;hello-world&#39; already exists in space &#39;default&#39;"
        in response.text
    )


def test_edit_record_editor_html_returns_200_with_record_values(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.get("/test/hello-world/edit")

    assert response.status_code == 200
    assert "<title>Edit Hello World</title>" in response.text
    assert '<form method="post" action="/test/hello-world/edit">' in response.text
    assert 'value="test"' in response.text
    assert 'value="hello-world"' in response.text
    assert 'value="Hello World"' in response.text
    assert "# Hello" in response.text
    assert 'value="test, integration"' in response.text
    assert '<a href="/test/hello-world">Cancel</a>' in response.text


def test_update_record_from_editor_redirects_to_detail(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.post(
        "/test/hello-world/edit",
        data={
            "space": "test",
            "slug": "renamed-from-form",
            "title": "Renamed From Form",
            "body_markdown": "# Renamed",
            "tags": "updated, web",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/test/renamed-from-form"

    detail = client.get("/test/renamed-from-form")
    assert detail.status_code == 200
    assert "<h1>Renamed From Form</h1>" in detail.text
    assert "<h1>Renamed</h1>" in detail.text


def test_update_record_from_editor_returns_400_for_duplicate_slug(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload("first"))
    client.post("/api/records/", json=record_payload("second"))

    response = client.post(
        "/test/first/edit",
        data={
            "space": "test",
            "slug": "second",
            "title": "Duplicate",
            "body_markdown": "# Duplicate",
            "tags": "",
        },
    )

    assert response.status_code == 400
    assert (
        "Record with slug &#39;second&#39; already exists in space &#39;test&#39;" in response.text
    )


def test_update_record_from_editor_returns_400_for_invalid_payload(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.post(
        "/test/hello-world/edit",
        data={
            "space": "test",
            "slug": "Bad Slug",
            "title": "Hello World",
            "body_markdown": "# Hello",
            "tags": "test",
        },
    )

    assert response.status_code == 400
    assert 'role="alert"' in response.text
    assert "slug" in response.text


def test_edit_record_editor_html_returns_404_for_missing_record(client: TestClient) -> None:
    response = client.get("/test/not-found/edit")

    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"


def test_update_record_from_editor_returns_404_for_missing_record(client: TestClient) -> None:
    response = client.post(
        "/test/not-found/edit",
        data={
            "space": "test",
            "slug": "not-found",
            "title": "Missing",
            "body_markdown": "# Missing",
            "tags": "",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"


def test_view_record_html(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())

    response = client.get("/test/hello-world")

    assert response.status_code == 200
    assert "<title>Hello World</title>" in response.text
    assert '<meta name="robots" content="noindex,nofollow,noarchive">' in response.text
    assert '<a class="brand" href="/">MatrixedMind</a>' in response.text
    assert '<a href="/">Home</a>' in response.text
    assert '<a href="/test/hello-world/edit">Edit</a>' in response.text
    assert '<a href="/records/new">New page</a>' in response.text
    assert "GNU Affero General Public License v3.0" in response.text
    assert (
        '<a href="https://github.com/MatrixedMind/MatrixedMind">Source for this version</a>'
        in response.text
    )
    assert "<h1>Hello World</h1>" in response.text
    assert "<h1>Hello</h1>" in response.text


def test_public_record_html_remains_noindex_before_index_after(client: TestClient) -> None:
    client.post("/api/records/", json=record_payload())
    client.put("/api/records/test/hello-world", json={"visibility": "public"})

    response = client.get("/test/hello-world")

    assert response.status_code == 200
    assert '<meta name="robots" content="noindex,follow,noarchive">' in response.text


def test_public_record_html_is_indexable_after_index_after(client: TestClient) -> None:
    index_after = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    client.post(
        "/api/records/",
        json={**record_payload(), "visibility": "public", "index_after": index_after},
    )

    response = client.get("/test/hello-world")

    assert response.status_code == 200
    assert '<meta name="robots" content="index,follow,archive">' in response.text


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
    assert "<img>safe" in response.text
    assert 'src="x"' not in response.text
    assert "<script" not in response.text
    assert "onerror=" not in response.text
    assert "safe" in response.text


def test_view_record_html_renders_approved_https_markdown_image(client: TestClient) -> None:
    client.post(
        "/api/records/",
        json={
            **record_payload("safe-image"),
            "body_markdown": "![Diagram](https://images.example.com/diagram.png)",
        },
    )

    response = client.get("/test/safe-image")

    assert response.status_code == 200
    assert '<img src="https://images.example.com/diagram.png" alt="Diagram">' in response.text


def test_view_record_html_enforces_configured_image_source_allowlist(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "markdown_image_source_allowlist", "approved.example")
    client.post(
        "/api/records/",
        json={
            **record_payload("blocked-image"),
            "body_markdown": "![Blocked](https://attacker.example/image.png)",
        },
    )

    response = client.get("/test/blocked-image")

    assert response.status_code == 200
    assert "<img" not in response.text
    assert "Blocked" in response.text
