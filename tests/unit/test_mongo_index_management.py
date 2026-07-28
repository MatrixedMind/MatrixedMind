from unittest.mock import Mock

from app.adapters.mongo.repository import MongoRecordRepository
from app.adapters.mongo.security import MongoAuditEventRepository, MongoLlmTokenRepository


def test_mongo_adapters_can_skip_runtime_index_management() -> None:
    db = Mock()

    MongoRecordRepository(db, ensure_indexes=False)
    MongoLlmTokenRepository(db, ensure_indexes=False)
    MongoAuditEventRepository(db, ensure_indexes=False)

    db.records.create_index.assert_not_called()
    db.llm_api_tokens.create_index.assert_not_called()
    db.audit_events.create_index.assert_not_called()


def test_mongo_adapters_manage_indexes_by_default() -> None:
    db = Mock()

    MongoRecordRepository(db)
    MongoLlmTokenRepository(db)
    MongoAuditEventRepository(db)

    assert db.records.create_index.call_count == 2
    assert db.llm_api_tokens.create_index.call_count == 1
    assert db.audit_events.create_index.call_count == 2
