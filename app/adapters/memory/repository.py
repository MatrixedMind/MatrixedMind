"""Non-durable repository doubles used by tests and contract verification.

These adapters deliberately favor simple, inspectable state over production storage behavior.
They are not selectable by MatrixedMind runtime configuration and are not a supported persistence
backend for local or hosted Instances.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import AuditEvent, PersonalAccessToken, Record, RecordRevision
from app.domain.ports import (
    AuditEventRepository,
    AutomationWriteRepository,
    PersonalAccessTokenRepository,
    RecordRepository,
)


class InMemoryTestRecordRepository(RecordRepository):
    """Linear, process-local RecordRepository test double; never a production backend."""

    def __init__(self) -> None:
        self.records: list[Record] = []

    def get_by_slug(self, owner_id: str, space: str, slug: str) -> Record | None:
        for r in self.records:
            if r.owner_id == owner_id and r.space == space and r.slug == slug:
                return r
        return None

    def list_children(self, owner_id: str, space: str, parent_id: str | None) -> list[Record]:
        return [
            r
            for r in self.records
            if r.owner_id == owner_id and r.space == space and r.parent_id == parent_id
        ]

    def create(self, record: Record) -> Record:
        if self.get_by_slug(record.owner_id, record.space, record.slug) is not None:
            raise ValueError(
                "record already exists for "
                f"owner_id={record.owner_id!r} space={record.space!r} slug={record.slug!r}"
            )
        if not record.id:
            record.id = str(len(self.records) + 1)
        self.records.append(record)
        return record

    def update(self, owner_id: str, record_id: str, record: Record, actor_id: str) -> Record:
        for i, r in enumerate(self.records):
            if r.id == record_id and r.owner_id == owner_id:
                if record.owner_id != owner_id:
                    raise ValueError("record owner_id cannot change during update")
                conflict = self.get_by_slug(owner_id, record.space, record.slug)
                if conflict is not None and conflict.id != record_id:
                    raise ValueError(
                        "record already exists for "
                        f"owner_id={record.owner_id!r} space={record.space!r} "
                        f"slug={record.slug!r}"
                    )
                now = datetime.now(UTC)
                revision = RecordRevision(
                    revision_id=str(uuid4()),
                    author_id=r.updated_by,
                    timestamp=now,
                    body_markdown=r.body_markdown,
                )
                record.id = record_id
                record.created_at = r.created_at
                record.created_by = r.created_by
                record.updated_at = now
                record.updated_by = actor_id
                record.revisions = [*r.revisions, revision]
                self.records[i] = record
                return record
        raise KeyError(f"record not found: {record_id}")


class InMemoryTestPersonalAccessTokenRepository(PersonalAccessTokenRepository):
    """Process-local personal-access-token repository for tests and contracts only."""

    def __init__(self) -> None:
        self.tokens_by_id: dict[str, PersonalAccessToken] = {}
        self.token_ids_by_hash: dict[str, str] = {}

    def get_by_hash(self, token_hash: str) -> PersonalAccessToken | None:
        token_id = self.token_ids_by_hash.get(token_hash)
        return self.tokens_by_id.get(token_id) if token_id is not None else None

    def save(self, token: PersonalAccessToken) -> PersonalAccessToken:
        matching_id = self.token_ids_by_hash.get(token.token_hash)
        if matching_id is not None and matching_id != token.id:
            raise ValueError(f"token hash already exists: {token.token_hash}")

        previous = self.tokens_by_id.get(token.id)
        stored = token
        if previous is not None and previous.revoked_at is not None:
            stored = token.model_copy(update={"revoked_at": previous.revoked_at})
        if previous is not None and previous.token_hash != token.token_hash:
            del self.token_ids_by_hash[previous.token_hash]
        self.tokens_by_id[stored.id] = stored
        self.token_ids_by_hash[stored.token_hash] = stored.id
        return stored

    def revoke(self, token_id: str) -> None:
        token = self.tokens_by_id.get(token_id)
        if token is None:
            raise KeyError(f"token not found: {token_id}")
        if not token.is_revoked:
            self.tokens_by_id[token_id] = token.model_copy(update={"revoked_at": datetime.now(UTC)})


class InMemoryTestAuditEventRepository(AuditEventRepository):
    """Process-local audit-event repository for tests and contracts only."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event


class InMemoryTestAutomationWriteRepository(AutomationWriteRepository):
    """Snapshot-based atomic-write test double for repository contract verification."""

    def __init__(
        self,
        records: InMemoryTestRecordRepository,
        audits: InMemoryTestAuditEventRepository,
    ) -> None:
        self.records = records
        self.audits = audits

    def upsert_record_with_audit(
        self,
        record: Record,
        *,
        actor_id: str,
        audit_event_id: str,
    ) -> Record:
        record_snapshot = [existing.model_copy(deep=True) for existing in self.records.records]
        audit_snapshot = [event.model_copy(deep=True) for event in self.audits.events]
        try:
            existing = self.records.get_by_slug(record.owner_id, record.space, record.slug)
            if existing is None:
                saved = self.records.create(record)
                action = "record.created"
            else:
                if existing.id is None:
                    raise ValueError("record has no stable identifier")
                saved = self.records.update(
                    record.owner_id,
                    existing.id,
                    record,
                    actor_id=actor_id,
                )
                action = "record.updated"

            self.audits.append(
                AuditEvent(
                    id=audit_event_id,
                    actor_id=actor_id,
                    action=action,
                    target_type="record",
                    target_id=saved.id or f"{saved.space}/{saved.slug}",
                    details={"space": saved.space, "slug": saved.slug, "source": "llm_api"},
                )
            )
        except Exception:
            self.records.records[:] = record_snapshot
            self.audits.events[:] = audit_snapshot
            raise
        return saved
