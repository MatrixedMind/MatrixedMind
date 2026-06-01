from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

from app.settings import settings


class MongoConnection:
    client: MongoClient[dict[str, Any]] | None = None
    db: Database[dict[str, Any]] | None = None

    @classmethod
    def connect(cls) -> None:
        if cls.client is None:
            cls.client = MongoClient(settings.mongo_uri)
            db_name = settings.mongo_uri.split("/")[-1].split("?")[0] or "matrixed_mind"
            cls.db = cls.client[db_name]

    @classmethod
    def disconnect(cls) -> None:
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None

    @classmethod
    def get_db(cls) -> Database[dict[str, Any]]:
        if cls.db is None:
            cls.connect()
        assert cls.db is not None
        return cls.db
