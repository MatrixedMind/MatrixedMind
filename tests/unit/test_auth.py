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


def test_production_settings_accept_managed_runtime_secrets() -> None:
    production = Settings(
        app_env="production",
        auth_mode="production",
        app_secret_key="app-secret",
        llm_token_pepper="llm-pepper",
    )

    assert production.app_secret_key is not None
    assert production.llm_token_pepper is not None


def test_issued_llm_token_is_only_represented_by_hash() -> None:
    raw_token = issue_llm_token()
    token_hash = hash_llm_token(raw_token)
    assert raw_token != token_hash
    assert len(token_hash) == 64
