from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_env: str = "local"
    mongo_uri: str = (
        "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?authSource=admin"
    )


settings = Settings()
