from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_env: str = "local"
    mongo_uri: str = "mongodb://wiki:wiki@localhost:27017/wiki?authSource=admin"


settings = Settings()
