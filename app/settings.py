from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.rendering import normalize_image_source_allowlist


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

    @field_validator("markdown_image_source_allowlist")
    @classmethod
    def validate_markdown_image_source_allowlist(cls, value: str) -> str:
        normalize_image_source_allowlist(value)
        return value

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
