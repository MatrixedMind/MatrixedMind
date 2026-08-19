from datetime import UTC, datetime
from uuid import uuid4

from app.adapters.memory.repository import (
    InMemoryTestAuditEventRepository,
    InMemoryTestRecordRepository,
)
from app.domain.models import Record, RecordRevision
from app.domain.ports import AutomationWriteRepository


def assert_automation_write_repository_contract(
    writes: AutomationWriteRepository,
    records: InMemoryTestRecordRepository,
    audits: InMemoryTestAuditEventRepository,
) -> None:
    created = writes.upsert_record_with_audit(
        _automation_record("# Created"),
        actor_id="automation:test",
        audit_event_id="audit-create",
    )

    assert created.id is not None
    assert len(created.revisions) == 1
    assert [event.action for event in audits.events] == ["record.created"]
    assert audits.events[0].target_id == created.id

    updated = writes.upsert_record_with_audit(
        _automation_record("# Updated"),
        actor_id="automation:test",
        audit_event_id="audit-update",
    )

    assert updated.id == created.id
    assert updated.body_markdown == "# Updated"
    assert len(updated.revisions) == 2
    assert records.get_by_slug("owner", "personal", "automation") == updated
    assert [event.action for event in audits.events] == ["record.created", "record.updated"]


def _automation_record(body: str) -> Record:
    return Record(
        space="personal",
        slug="automation",
        title="Automation",
        body_markdown=body,
        owner_id="owner",
        created_by="automation:test",
        updated_by="automation:test",
        revisions=[
            RecordRevision(
                revision_id=str(uuid4()),
                author_id="automation:test",
                timestamp=datetime.now(UTC),
                body_markdown=body,
            )
        ],
    )
