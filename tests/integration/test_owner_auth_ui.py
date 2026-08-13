from collections.abc import Iterator
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.adapters.memory.auth import InMemoryTestOwnerAuthRepository
from app.adapters.memory.repository import InMemoryTestRecordRepository
from app.auth.dependencies import get_owner_auth_repository
from app.auth.service import authentication_attempt_limiter, issue_operator_credential
from app.dependencies import get_record_repository
from app.main import app
from app.settings import settings

PASSWORD = "correct horse battery staple"


@pytest.fixture
def auth_repo() -> InMemoryTestOwnerAuthRepository:
    return InMemoryTestOwnerAuthRepository()


@pytest.fixture
def client(
    auth_repo: InMemoryTestOwnerAuthRepository, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "auth_mode", "local")
    app.dependency_overrides[get_owner_auth_repository] = lambda: auth_repo
    record_repo = InMemoryTestRecordRepository()
    app.dependency_overrides[get_record_repository] = lambda: record_repo
    authentication_attempt_limiter.clear()
    try:
        yield TestClient(app, base_url="http://testserver")
    finally:
        app.dependency_overrides.clear()
        authentication_attempt_limiter.clear()


def form_headers(origin: str = "http://testserver") -> dict[str, str]:
    return {"Origin": origin, "Content-Type": "application/x-www-form-urlencoded"}


def setup_owner(client: TestClient, repo: InMemoryTestOwnerAuthRepository) -> None:
    credential = issue_operator_credential(repo, "bootstrap", settings)
    response = client.post(
        "/setup",
        content=urlencode(
            {
                "operator_credential": credential,
                "display_name": "Mind Owner",
                "password": PASSWORD,
                "password_confirmation": PASSWORD,
            }
        ),
        headers=form_headers(),
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_setup_login_logout_and_cookie_security(
    client: TestClient, auth_repo: InMemoryTestOwnerAuthRepository
) -> None:
    setup_owner(client, auth_repo)
    cookie = client.cookies.get(settings.session_cookie_name)
    assert cookie is not None
    assert client.get("/").status_code == 200
    assert "Your Mind" in client.get("/").text

    csrf = client.cookies.get(settings.csrf_cookie_name)
    response = client.post(
        "/logout",
        content=urlencode({"csrf_token": csrf}),
        headers=form_headers(),
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert client.get("/", follow_redirects=False).status_code == 303

    login = client.post(
        "/login",
        content=urlencode({"password": PASSWORD}),
        headers=form_headers(),
        follow_redirects=False,
    )
    assert login.status_code == 303
    session_cookie = next(
        header
        for header in login.headers.get_list("set-cookie")
        if settings.session_cookie_name in header
    )
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Path=/" in session_cookie
    assert "Max-Age=2592000" in session_cookie
    assert "Secure" not in session_cookie


def test_production_session_cookie_is_secure(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import Response

    from app.auth.dependencies import set_session_cookies

    monkeypatch.setattr(settings, "app_env", "production")
    response = Response()
    set_session_cookies(response, "session", "csrf")
    assert all("Secure" in header for header in response.headers.getlist("set-cookie"))


def test_setup_and_login_require_same_origin(
    client: TestClient, auth_repo: InMemoryTestOwnerAuthRepository
) -> None:
    credential = issue_operator_credential(auth_repo, "bootstrap", settings)
    payload = urlencode(
        {
            "operator_credential": credential,
            "display_name": "Owner",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        }
    )
    assert (
        client.post(
            "/setup", content=payload, headers=form_headers("https://evil.example")
        ).status_code
        == 403
    )
    assert client.post("/setup", content=payload).status_code == 403


def test_authentication_form_body_limit(client: TestClient) -> None:
    oversized = "x" * (settings.auth_form_body_limit_bytes + 1)
    response = client.post(
        "/login",
        content=oversized,
        headers=form_headers(),
    )
    assert response.status_code == 413


def test_authenticated_write_rejects_missing_csrf(
    client: TestClient, auth_repo: InMemoryTestOwnerAuthRepository
) -> None:
    setup_owner(client, auth_repo)
    response = client.post(
        "/records/new",
        content=urlencode(
            {"space": "default", "slug": "hello", "title": "Hello", "body_markdown": "Hi"}
        ),
        headers=form_headers(),
    )
    assert response.status_code == 403


def test_cookie_authenticated_json_writes_require_origin_and_csrf_header(
    client: TestClient, auth_repo: InMemoryTestOwnerAuthRepository
) -> None:
    setup_owner(client, auth_repo)
    payload = {
        "space": "default",
        "slug": "api-page",
        "title": "API Page",
        "body_markdown": "# API Page",
    }
    csrf = client.cookies.get(settings.csrf_cookie_name)
    assert csrf is not None
    assert (
        client.post(
            "/api/records/", json=payload, headers={"Origin": "http://testserver"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/records/",
            json=payload,
            headers={"Origin": "http://testserver", "X-CSRF-Token": "wrong"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/records/",
            json=payload,
            headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    response = client.post(
        "/api/records/",
        json=payload,
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 201
    update_url = "/api/records/default/api-page"
    update = {"title": "Updated API Page"}
    assert (
        client.put(update_url, json=update, headers={"Origin": "http://testserver"}).status_code
        == 403
    )
    assert (
        client.put(
            update_url,
            json=update,
            headers={"Origin": "http://testserver", "X-CSRF-Token": "wrong"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            update_url,
            json=update,
            headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert (
        client.put(
            update_url,
            json=update,
            headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
        ).status_code
        == 200
    )


def test_password_change_keeps_current_session_and_revokes_other_session(
    client: TestClient, auth_repo: InMemoryTestOwnerAuthRepository
) -> None:
    setup_owner(client, auth_repo)
    other = TestClient(app, base_url="http://testserver")
    login = other.post(
        "/login",
        content=urlencode({"password": PASSWORD}),
        headers=form_headers(),
        follow_redirects=False,
    )
    assert login.status_code == 303
    csrf = client.cookies.get(settings.csrf_cookie_name)
    changed = client.post(
        "/settings/password",
        content=urlencode(
            {
                "csrf_token": csrf,
                "current_password": PASSWORD,
                "password": "another secure owner password",
                "password_confirmation": "another secure owner password",
            }
        ),
        headers=form_headers(),
        follow_redirects=False,
    )
    assert changed.status_code == 303
    assert client.get("/").status_code == 200
    assert other.get("/", follow_redirects=False).status_code == 303


def test_recovery_changes_password_and_revokes_every_session(
    client: TestClient, auth_repo: InMemoryTestOwnerAuthRepository
) -> None:
    setup_owner(client, auth_repo)
    credential = issue_operator_credential(auth_repo, "recovery", settings)
    response = client.post(
        "/recovery",
        content=urlencode(
            {
                "operator_credential": credential,
                "password": "recovered secure owner password",
                "password_confirmation": "recovered secure owner password",
            }
        ),
        headers=form_headers(),
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert client.get("/", follow_redirects=False).status_code == 303
    assert (
        client.post(
            "/login",
            content=urlencode({"password": "recovered secure owner password"}),
            headers=form_headers(),
            follow_redirects=False,
        ).status_code
        == 303
    )


def test_public_and_protected_routes_and_security_headers(client: TestClient) -> None:
    for path in ("/health", "/source", "/openapi-llm.json", "/login", "/setup", "/recovery"):
        response = client.get(path)
        assert response.status_code != 401
    denied = client.get("/", follow_redirects=False)
    assert denied.status_code == 303
    assert denied.headers["location"] == "/login"
    assert "frame-ancestors 'none'" in denied.headers["content-security-policy"]
    assert denied.headers["x-content-type-options"] == "nosniff"
    assert denied.headers["referrer-policy"] == "same-origin"
    assert client.get("/login").headers["cache-control"] == "no-store"


def test_clean_local_startup_uses_no_optional_identity_provider_packages() -> None:
    assert settings.identity_provider == "local"
    assert "firebase" not in __import__("sys").modules
    assert "authlib" not in __import__("sys").modules
