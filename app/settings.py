from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_env: Literal["local", "test", "production"] = "local"
    auth_mode: Literal["dev", "test", "production"] = "dev"
    llm_request_body_limit_bytes: int = 65_536
    llm_rate_limit_requests: int = 60
    llm_rate_limit_window_seconds: int = 60
    mongo_uri: str = (
        "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?authSource=admin"
    )

    @model_validator(mode="after")
    def production_fails_closed(self) -> "Settings":
        if self.app_env == "production" and self.auth_mode != "production":
            raise ValueError("production APP_ENV requires AUTH_MODE=production")
        if self.app_env != "production" and self.auth_mode == "production":
            raise ValueError("production auth may only be enabled in production APP_ENV")
        return self


settings = Settings()
