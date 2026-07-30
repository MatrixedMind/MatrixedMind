import pytest
from fastapi import HTTPException

from app.auth.dependencies import get_current_user, hash_llm_token, issue_llm_token
from app.settings import Settings, settings


@pytest.mark.anyio
async def test_dev_auth_returns_deterministic_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_mode", "dev")
    user = await get_current_user()
    assert user.id == "dev-user"


@pytest.mark.anyio
async def test_test_auth_requires_explicit_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_mode", "test")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user()
    assert exc_info.value.status_code == 401


def test_production_settings_fail_closed() -> None:
    with pytest.raises(ValueError, match="requires AUTH_MODE=production"):
        Settings(app_env="production", auth_mode="dev")


def test_production_settings_require_managed_runtime_secrets() -> None:
    with pytest.raises(ValueError, match="requires managed runtime secrets"):
        Settings(app_env="production", auth_mode="production")


@pytest.mark.parametrize(
    ("app_secret_key", "llm_token_pepper"),
    [
        ("", "llm-pepper"),
        ("   ", "llm-pepper"),
        ("app-secret", ""),
        ("app-secret", "\t"),
    ],
)
def test_production_settings_reject_blank_managed_runtime_secrets(
    app_secret_key: str,
    llm_token_pepper: str,
) -> None:
    with pytest.raises(ValueError, match="requires managed runtime secrets"):
        Settings(
            app_env="production",
            auth_mode="production",
            app_secret_key=app_secret_key,
            llm_token_pepper=llm_token_pepper,
        )


def test_production_settings_accept_managed_runtime_secrets() -> None:
    production = Settings(
        app_env="production",
        auth_mode="production",
        app_secret_key="app-secret",
        llm_token_pepper="llm-pepper",
        llm_api_server_url="https://matrixedmind.example",
    )

    assert production.app_secret_key is not None
    assert production.llm_token_pepper is not None


def test_production_settings_require_llm_api_server_url() -> None:
    with pytest.raises(ValueError, match="requires LLM_API_SERVER_URL"):
        Settings(
            app_env="production",
            auth_mode="production",
            app_secret_key="app-secret",
            llm_token_pepper="llm-pepper",
        )


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


def test_issued_llm_token_is_only_represented_by_hash() -> None:
    raw_token = issue_llm_token()
    token_hash = hash_llm_token(raw_token)
    assert raw_token != token_hash
    assert len(token_hash) == 64
