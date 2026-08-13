import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.rendering import normalize_image_source_allowlist

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_env: Literal["local", "test", "production"] = "local"
    auth_mode: Literal["local", "test"] = "local"
    identity_provider: Literal["local", "firebase", "oidc"] = "local"
    session_cookie_name: str = "matrixedmind_session"
    csrf_cookie_name: str = "matrixedmind_csrf"
    session_inactivity_seconds: int = 30 * 24 * 60 * 60
    session_absolute_seconds: int = 90 * 24 * 60 * 60
    session_rotation_seconds: int = 8 * 60 * 60
    operator_credential_ttl_seconds: int = 15 * 60
    auth_attempt_limit: int = 5
    auth_attempt_window_seconds: int = 15 * 60
    auth_form_body_limit_bytes: int = 16_384
    llm_request_body_limit_bytes: int = 65_536
    llm_rate_limit_requests: int = 60
    llm_rate_limit_window_seconds: int = 60
    llm_api_server_url: str | None = None
    markdown_image_source_allowlist: str = ""
    mongo_ensure_indexes: bool = True
    mongo_uri: str = (
        "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?"
        "authSource=admin&replicaSet=rs0&directConnection=true&retryWrites=false"
    )
    source_repository_url: str = "https://github.com/MatrixedMind/MatrixedMind"
    source_revision: str = "local"

    @field_validator("markdown_image_source_allowlist")
    @classmethod
    def validate_markdown_image_source_allowlist(cls, value: str) -> str:
        normalize_image_source_allowlist(value)
        return value

    @field_validator("llm_api_server_url")
    @classmethod
    def validate_llm_api_server_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("LLM_API_SERVER_URL must be a public HTTPS origin")
        return value.rstrip("/")

    @field_validator("source_repository_url")
    @classmethod
    def validate_source_repository_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("SOURCE_REPOSITORY_URL must be a public HTTPS repository URL")
        return value.rstrip("/")

    @field_validator("source_revision")
    @classmethod
    def validate_source_revision(cls, value: str) -> str:
        if value != "local" and not _COMMIT_SHA_PATTERN.fullmatch(value):
            raise ValueError("SOURCE_REVISION must be 'local' or a full lowercase Git commit SHA")
        return value

    @field_validator(
        "session_inactivity_seconds",
        "session_absolute_seconds",
        "session_rotation_seconds",
        "operator_credential_ttl_seconds",
        "auth_attempt_limit",
        "auth_attempt_window_seconds",
        "auth_form_body_limit_bytes",
    )
    @classmethod
    def validate_positive_duration(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("authentication durations must be positive")
        return value

    @property
    def source_offer_url(self) -> str:
        if _COMMIT_SHA_PATTERN.fullmatch(self.source_revision):
            return f"{self.source_repository_url}/tree/{self.source_revision}"
        return self.source_repository_url

    @model_validator(mode="after")
    def production_fails_closed(self) -> "Settings":
        if self.app_env == "production" and self.auth_mode != "local":
            raise ValueError("production APP_ENV requires AUTH_MODE=local")
        if self.auth_mode == "test" and self.app_env != "test":
            raise ValueError("AUTH_MODE=test requires APP_ENV=test")
        if self.identity_provider != "local":
            raise ValueError("only the local identity provider is implemented")
        if self.session_rotation_seconds > self.session_absolute_seconds:
            raise ValueError("session rotation must not exceed absolute expiration")
        if self.app_env == "production" and self.llm_api_server_url is None:
            raise ValueError("production APP_ENV requires LLM_API_SERVER_URL")
        return self


settings = Settings()
