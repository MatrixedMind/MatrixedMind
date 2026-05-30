from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    mongo_uri: str = "mongodb://wiki:wiki@localhost:27017/wiki?authSource=admin"

    class Config:
        env_file = ".env"


settings = Settings()
