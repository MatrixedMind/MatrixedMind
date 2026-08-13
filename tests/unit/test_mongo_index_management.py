from unittest.mock import Mock

from app.adapters.mongo.repository import MongoRecordRepository
from app.adapters.mongo.security import (
    MongoAuditEventRepository,
    MongoPersonalAccessTokenRepository,
)


def test_mongo_adapters_can_skip_runtime_index_management() -> None:
    db = Mock()

    MongoRecordRepository(db, ensure_indexes=False)
    MongoPersonalAccessTokenRepository(db, ensure_indexes=False)
    MongoAuditEventRepository(db, ensure_indexes=False)

    db.records.create_index.assert_not_called()
    db.personal_access_tokens.create_index.assert_not_called()
    db.audit_events.create_index.assert_not_called()


def test_mongo_adapters_manage_indexes_by_default() -> None:
    db = Mock()

    MongoRecordRepository(db)
    MongoPersonalAccessTokenRepository(db)
    MongoAuditEventRepository(db)

    assert db.records.create_index.call_count == 2
    assert db.personal_access_tokens.create_index.call_count == 1
    db.personal_access_tokens.create_index.assert_called_once_with(
        [("token_hash", 1)],
        unique=True,
        name="personal_access_tokens_token_hash_unique",
    )
    assert db.audit_events.create_index.call_count == 2
