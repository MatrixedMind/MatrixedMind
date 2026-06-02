from app.adapters.mongo.connection import MongoConnection
from app.settings import settings

LOCAL_MONGO_URI = (
    "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?authSource=admin"
)


def test_mongo_connection_can_ping_local_database() -> None:
    MongoConnection.disconnect()
    settings.mongo_uri = LOCAL_MONGO_URI

    assert MongoConnection.ping() is True
