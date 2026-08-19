from datetime import UTC, datetime, timedelta

import pytest
from starlette.requests import Request

import app.auth.dependencies as auth_dependencies
from app.auth.dependencies import (
    hash_personal_access_token,
    issue_personal_access_token,
    require_browser_csrf,
)
from app.settings import Settings, settings


def test_local_auth_is_the_default() -> None:
    configured = Settings(_env_file=None)
    assert configured.auth_mode == "local"
    assert configured.identity_provider == "local"


def test_test_auth_is_confined_to_test_environment() -> None:
    with pytest.raises(ValueError, match="AUTH_MODE=test requires APP_ENV=test"):
        Settings(app_env="local", auth_mode="test")
    assert Settings(app_env="test", auth_mode="test").auth_mode == "test"


def test_production_settings_fail_closed() -> None:
    with pytest.raises(ValueError, match="AUTH_MODE=local"):
        Settings(app_env="production", auth_mode="test", llm_api_server_url="https://example.com")


def test_production_settings_require_llm_api_server_url() -> None:
    with pytest.raises(ValueError, match="requires LLM_API_SERVER_URL"):
        Settings(app_env="production", auth_mode="local")


def test_production_settings_accept_local_auth_without_app_secret() -> None:
    production = Settings(
        app_env="production",
        auth_mode="local",
        llm_api_server_url="https://matrixedmind.example",
    )
    assert production.auth_mode == "local"


def test_optional_identity_provider_is_fail_closed_until_adapter_exists() -> None:
    with pytest.raises(ValueError, match="only the local identity provider"):
        Settings(identity_provider="oidc")


@pytest.mark.parametrize(
    "server_url",
    [
        "http://matrixedmind.example",
        "https://user@matrixedmind.example",
        "https://matrixedmind.example/openapi-llm.json",
        "https://matrixedmind.example?source=test",
        "https://matrixedmind.example#fragment",
    ],
)
def test_settings_reject_invalid_llm_api_server_url(server_url: str) -> None:
    with pytest.raises(ValueError, match="LLM_API_SERVER_URL"):
        Settings(llm_api_server_url=server_url)


@pytest.mark.parametrize(
    "image_source_allowlist",
    [
        "https://images.example.com",
        "images.example.com/path",
        "images.example.com:443",
        "user@images.example.com",
        "*.",
        ".example.com",
        "-images.example.com",
        "images-.example.com",
        "localhost",
    ],
)
def test_settings_reject_invalid_image_source_allowlist(
    image_source_allowlist: str,
) -> None:
    with pytest.raises(ValueError, match="exact hostnames or .* wildcards"):
        Settings(markdown_image_source_allowlist=image_source_allowlist)


def test_settings_accept_exact_and_wildcard_image_sources() -> None:
    configured = Settings(
        markdown_image_source_allowlist="images.example.com, *.usercontent.example"
    )
    assert configured.markdown_image_source_allowlist == (
        "images.example.com, *.usercontent.example"
    )


@pytest.mark.parametrize(
    ("repository_url", "revision"),
    [
        ("http://example.com/source", "local"),
        ("https://user@example.com/source", "local"),
        ("https://example.com/source?branch=main", "local"),
        ("https://example.com/source", "main"),
        ("https://example.com/source", "ABCDEF" * 6 + "ABCD"),
    ],
)
def test_settings_reject_invalid_source_offer_configuration(
    repository_url: str,
    revision: str,
) -> None:
    with pytest.raises(ValueError):
        Settings(source_repository_url=repository_url, source_revision=revision)


def test_source_offer_points_to_the_exact_deployed_revision() -> None:
    revision = "a" * 40
    configured = Settings(
        source_repository_url="https://example.com/owner/repository/",
        source_revision=revision,
    )
    assert configured.source_offer_url == f"https://example.com/owner/repository/tree/{revision}"


def test_issued_personal_access_token_is_only_represented_by_hash() -> None:
    raw_token = issue_personal_access_token()
    token_hash = hash_personal_access_token(raw_token)
    assert raw_token != token_hash
    assert len(token_hash) == 64


def test_test_identity_csrf_bypass_handles_leap_day(monkeypatch: pytest.MonkeyPatch) -> None:
    leap_day = datetime(2028, 2, 29, tzinfo=UTC)
    monkeypatch.setattr(settings, "auth_mode", "test")
    monkeypatch.setattr(auth_dependencies, "utc_now", lambda: leap_day)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/records/",
            "headers": [(b"x-test-user-id", b"owner")],
        }
    )

    session = require_browser_csrf(request, None)

    assert session.absolute_expires_at == leap_day + timedelta(days=365)
