from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import AuditEvent, LlmApiToken, Record, RecordRevision
from app.domain.ports import AuditEventRepository, LlmTokenRepository, RecordRepository


class InMemoryRecordRepository(RecordRepository):
    def __init__(self) -> None:
        self.records: list[Record] = []

    def get_by_slug(self, space: str, slug: str) -> Record | None:
        for r in self.records:
            if r.space == space and r.slug == slug:
                return r
        return None

    def list_children(self, space: str, parent_id: str | None) -> list[Record]:
        return [r for r in self.records if r.space == space and r.parent_id == parent_id]

    def create(self, record: Record) -> Record:
        if not record.id:
            record.id = str(len(self.records) + 1)
        self.records.append(record)
        return record

    def update(self, record_id: str, record: Record, actor_id: str = "system") -> Record:
        for i, r in enumerate(self.records):
            if r.id == record_id:
                now = datetime.now(UTC)
                revision = RecordRevision(
                    revision_id=str(uuid4()),
                    author_id=r.updated_by,
                    timestamp=now,
                    body_markdown=r.body_markdown,
                )
                record.id = record_id
                record.created_at = r.created_at
                record.updated_at = now
                record.updated_by = actor_id
                record.revisions = [*r.revisions, revision]
                self.records[i] = record
                return record
        raise KeyError(f"record not found: {record_id}")


class InMemoryLlmTokenRepository(LlmTokenRepository):
    def __init__(self) -> None:
        self.tokens: dict[str, LlmApiToken] = {}

    def get_by_hash(self, token_hash: str) -> LlmApiToken | None:
        return self.tokens.get(token_hash)

    def save(self, token: LlmApiToken) -> LlmApiToken:
        self.tokens[token.token_hash] = token
        return token

    def revoke(self, token_id: str) -> None:
        for token_hash, token in self.tokens.items():
            if token.id == token_id:
                self.tokens[token_hash] = token.model_copy(update={"revoked_at": datetime.now(UTC)})
                return
        raise KeyError(f"token not found: {token_id}")


class InMemoryAuditEventRepository(AuditEventRepository):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event
