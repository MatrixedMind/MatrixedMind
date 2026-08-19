import pytest

from app.adapters.memory.repository import (
    InMemoryTestAuditEventRepository,
    InMemoryTestAutomationWriteRepository,
    InMemoryTestRecordRepository,
)
from app.domain.models import AuditEvent, Record
from tests.contracts.automation_write_repository_contract import (
    assert_automation_write_repository_contract,
)


class AppendThenFailAuditRepository(InMemoryTestAuditEventRepository):
    def append(self, event: AuditEvent) -> AuditEvent:
        super().append(event)
        raise RuntimeError("injected audit failure")


class WriteThenConflictRecordRepository(InMemoryTestRecordRepository):
    def create(self, record: Record) -> Record:
        super().create(record)
        raise ValueError("injected record conflict")


def test_in_memory_automation_write_repository_satisfies_contract() -> None:
    records = InMemoryTestRecordRepository()
    audits = InMemoryTestAuditEventRepository()

    assert_automation_write_repository_contract(
        InMemoryTestAutomationWriteRepository(records, audits),
        records,
        audits,
    )


def test_in_memory_automation_write_rolls_back_audit_and_record_on_audit_failure() -> None:
    records = InMemoryTestRecordRepository()
    audits = AppendThenFailAuditRepository()
    writes = InMemoryTestAutomationWriteRepository(records, audits)

    with pytest.raises(RuntimeError, match="injected audit failure"):
        writes.upsert_record_with_audit(
            _record(), actor_id="automation:test", audit_event_id="audit"
        )

    assert records.records == []
    assert audits.events == []


def test_in_memory_automation_write_rolls_back_on_record_conflict() -> None:
    records = WriteThenConflictRecordRepository()
    audits = InMemoryTestAuditEventRepository()
    writes = InMemoryTestAutomationWriteRepository(records, audits)

    with pytest.raises(ValueError, match="injected record conflict"):
        writes.upsert_record_with_audit(
            _record(), actor_id="automation:test", audit_event_id="audit"
        )

    assert records.records == []
    assert audits.events == []


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
