import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.rendering import normalize_image_source_allowlist

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_env: Literal["local", "test", "production"] = "local"
    app_secret_key: SecretStr | None = None
    auth_mode: Literal["dev", "test", "production"] = "dev"
    llm_request_body_limit_bytes: int = 65_536
    llm_rate_limit_requests: int = 60
    llm_rate_limit_window_seconds: int = 60
    llm_token_pepper: SecretStr | None = None
    markdown_image_source_allowlist: str = ""
    mongo_ensure_indexes: bool = True
    mongo_uri: str = (
        "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?authSource=admin"
    )
    source_repository_url: str = "https://github.com/MatrixedMind/MatrixedMind"
    source_revision: str = "local"

    @field_validator("markdown_image_source_allowlist")
    @classmethod
    def validate_markdown_image_source_allowlist(cls, value: str) -> str:
        normalize_image_source_allowlist(value)
        return value

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

    @property
    def source_offer_url(self) -> str:
        if _COMMIT_SHA_PATTERN.fullmatch(self.source_revision):
            return f"{self.source_repository_url}/tree/{self.source_revision}"
        return self.source_repository_url

    @model_validator(mode="after")
    def production_fails_closed(self) -> "Settings":
        if self.app_env == "production" and self.auth_mode != "production":
            raise ValueError("production APP_ENV requires AUTH_MODE=production")
        if self.app_env != "production" and self.auth_mode == "production":
            raise ValueError("production auth may only be enabled in production APP_ENV")
        managed_secrets = (self.app_secret_key, self.llm_token_pepper)
        if self.app_env == "production" and any(
            secret is None or not secret.get_secret_value().strip() for secret in managed_secrets
        ):
            raise ValueError("production APP_ENV requires managed runtime secrets")
        return self


settings = Settings()
