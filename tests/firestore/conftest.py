import os
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from pymongo import MongoClient

from app.adapters.mongo.repository import MongoRecordRepository

FIRESTORE_MONGO_URI_ENV = "FIRESTORE_MONGO_URI"


def _validated_firestore_uri() -> str:
    uri = os.getenv(FIRESTORE_MONGO_URI_ENV)
    if uri is None:
        pytest.skip(f"{FIRESTORE_MONGO_URI_ENV} is not configured")

    parsed = urlparse(uri)
    query = {key.lower(): values for key, values in parse_qs(parsed.query).items()}
    required_options = {
        "loadbalanced": "true",
        "authmechanism": "SCRAM-SHA-256",
        "tls": "true",
        "retrywrites": "false",
    }
    invalid_options = [
        f"{key}={expected}"
        for key, expected in required_options.items()
        if query.get(key, [None])[-1] != expected
    ]
    if parsed.hostname is None or not parsed.hostname.endswith(".firestore.goog"):
        invalid_options.append("a *.firestore.goog host")
    if invalid_options:
        pytest.fail(
            f"{FIRESTORE_MONGO_URI_ENV} must include " + ", ".join(invalid_options),
            pytrace=False,
        )
    return uri


@pytest.fixture(scope="session")
def firestore_mongo_uri() -> str:
    return _validated_firestore_uri()


@pytest.fixture
def firestore_client(
    firestore_mongo_uri: str,
) -> Iterator[MongoClient[dict[str, object]]]:
    client: MongoClient[dict[str, object]] = MongoClient(
        firestore_mongo_uri,
        serverSelectionTimeoutMS=10_000,
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def firestore_repo(
    firestore_client: MongoClient[dict[str, object]],
    firestore_mongo_uri: str,
) -> Iterator[MongoRecordRepository]:
    database_name = urlparse(firestore_mongo_uri).path.removeprefix("/")
    if not database_name:
        pytest.fail("FIRESTORE_MONGO_URI must include the Firestore database ID", pytrace=False)

    db = firestore_client[database_name]
    db.records.delete_many({})
    try:
        yield MongoRecordRepository(db)
    finally:
        db.records.delete_many({})
