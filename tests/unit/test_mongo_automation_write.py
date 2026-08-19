from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from app.adapters.mongo.repository import MongoAutomationWriteRepository
from app.domain.models import Record


def test_mongo_automation_write_commits_record_and_audit_in_one_session() -> None:
    db, session = _database_with_session()
    inserted_id = ObjectId()
    record = _record()
    stored = record.model_dump(exclude={"id"}) | {"_id": inserted_id}
    db.records.find_one.side_effect = [None, stored]
    db.records.insert_one.return_value.inserted_id = inserted_id
    writes = MongoAutomationWriteRepository(db, ensure_indexes=False)

    saved = writes.upsert_record_with_audit(
        record,
        actor_id="automation:test",
        audit_event_id="audit-create",
    )

    assert saved.id == str(inserted_id)
    db.records.insert_one.assert_called_once_with(
        record.model_dump(exclude={"id"}), session=session
    )
    audit_document = db.audit_events.insert_one.call_args.args[0]
    assert audit_document["action"] == "record.created"
    assert audit_document["target_id"] == str(inserted_id)
    assert db.audit_events.insert_one.call_args.kwargs == {"session": session}
    session.start_transaction.assert_called_once_with()
    session.commit_transaction.assert_called_once_with()
    session.abort_transaction.assert_not_called()


def test_mongo_automation_write_aborts_transaction_when_audit_insert_fails() -> None:
    db, session = _database_with_session()
    inserted_id = ObjectId()
    record = _record()
    stored = record.model_dump(exclude={"id"}) | {"_id": inserted_id}
    db.records.find_one.side_effect = [None, stored]
    db.records.insert_one.return_value.inserted_id = inserted_id
    db.audit_events.insert_one.side_effect = RuntimeError("injected audit failure")
    writes = MongoAutomationWriteRepository(db, ensure_indexes=False)

    with pytest.raises(RuntimeError, match="injected audit failure"):
        writes.upsert_record_with_audit(
            record,
            actor_id="automation:test",
            audit_event_id="audit-create",
        )

    session.abort_transaction.assert_called_once_with()
    session.commit_transaction.assert_not_called()


def _database_with_session() -> tuple[MagicMock, MagicMock]:
    db = MagicMock()
    session = MagicMock()
    db.client.start_session.return_value.__enter__.return_value = session
    return db, session


def _record() -> Record:
    return Record(
        space="personal",
        slug="automation",
        title="Automation",
        body_markdown="# Automation",
        owner_id="owner",
        created_by="automation:test",
        updated_by="automation:test",
    )
