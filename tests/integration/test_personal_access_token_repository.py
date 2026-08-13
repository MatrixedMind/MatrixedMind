from collections.abc import Iterator

import pytest
from pymongo import MongoClient

from app.adapters.mongo.security import MongoPersonalAccessTokenRepository
from tests.contracts.api_credential_repository_contract import (
    assert_personal_access_token_repository_contract,
)

LOCAL_MONGO_URI = (
    "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind"
    "?authSource=admin&replicaSet=rs0&directConnection=true&retryWrites=false"
)


@pytest.fixture
def repo() -> Iterator[MongoPersonalAccessTokenRepository]:
    client: MongoClient[dict[str, object]] = MongoClient(
        LOCAL_MONGO_URI,
        serverSelectionTimeoutMS=2000,
    )
    db = client.matrixed_mind_test
    db.llm_api_tokens.drop()
    try:
        yield MongoPersonalAccessTokenRepository(db)
    finally:
        db.llm_api_tokens.drop()
        client.close()


def test_mongo_personal_access_token_repository_satisfies_contract(
    repo: MongoPersonalAccessTokenRepository,
) -> None:
    assert_personal_access_token_repository_contract(repo)
