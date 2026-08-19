from collections.abc import Iterator

import pytest
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.adapters.mongo.repository import MongoAutomationWriteRepository
from app.domain.models import Record

LOCAL_MONGO_URI = (
    "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind"
    "?authSource=admin&replicaSet=rs0&directConnection=true&retryWrites=false"
)


@pytest.fixture
def mongo_writes() -> Iterator[tuple[MongoAutomationWriteRepository, Database[dict[str, object]]]]:
    client: MongoClient[dict[str, object]] = MongoClient(
        LOCAL_MONGO_URI,
        serverSelectionTimeoutMS=2000,
    )
    db = client.matrixed_mind_automation_test
    db.records.drop()
    db.audit_events.drop()
    try:
        yield MongoAutomationWriteRepository(db), db
    finally:
        db.records.drop()
        db.audit_events.drop()
        client.close()


def test_mongo_automation_write_commits_create_update_revision_and_one_audit_each(
    mongo_writes: tuple[MongoAutomationWriteRepository, Database[dict[str, object]]],
) -> None:
    writes, db = mongo_writes
    created = writes.upsert_record_with_audit(
        _record("# Created"),
        actor_id="automation:test",
        audit_event_id="audit-create",
    )
    updated = writes.upsert_record_with_audit(
        _record("# Updated"),
        actor_id="automation:test",
        audit_event_id="audit-update",
    )

    assert updated.id == created.id
    assert updated.body_markdown == "# Updated"
    assert len(updated.revisions) == 1
    assert db.records.count_documents({}) == 1
    assert [event["action"] for event in db.audit_events.find().sort("timestamp", ASCENDING)] == [
        "record.created",
        "record.updated",
    ]


def test_mongo_automation_write_aborts_record_when_audit_conflicts(
    mongo_writes: tuple[MongoAutomationWriteRepository, Database[dict[str, object]]],
) -> None:
    writes, db = mongo_writes
    db.audit_events.create_index("id", unique=True, name="test_audit_id_unique")
    db.audit_events.insert_one({"id": "audit-conflict"})

    with pytest.raises(DuplicateKeyError):
        writes.upsert_record_with_audit(
            _record("# Must roll back"),
            actor_id="automation:test",
            audit_event_id="audit-conflict",
        )

    assert db.records.count_documents({}) == 0
    assert db.audit_events.count_documents({}) == 1


def _record(body: str) -> Record:
    return Record(
        space="personal",
        slug="automation",
        title="Automation",
        body_markdown=body,
        owner_id="owner",
        created_by="automation:test",
        updated_by="automation:test",
    )
