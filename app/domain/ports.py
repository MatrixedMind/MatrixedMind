from datetime import datetime
from typing import Protocol

from .models import (
    AuditEvent,
    BrowserSession,
    OneTimeCredential,
    OneTimeCredentialPurpose,
    OwnerCredential,
    PersonalAccessToken,
    Record,
)


class RecordRepository(Protocol):
    """Storage contract for Markdown records."""

    def get_by_slug(self, owner_id: str, space: str, slug: str) -> Record | None: ...
    def list_children(self, owner_id: str, space: str, parent_id: str | None) -> list[Record]: ...
    def create(self, record: Record) -> Record: ...
    # Raises KeyError when record_id does not identify an existing record.
    def update(self, owner_id: str, record_id: str, record: Record, actor_id: str) -> Record: ...


class PersonalAccessTokenRepository(Protocol):
    def get_by_hash(self, token_hash: str) -> PersonalAccessToken | None: ...
    def save(self, token: PersonalAccessToken) -> PersonalAccessToken: ...
    def revoke(self, token_id: str) -> None: ...


class OwnerAuthRepository(Protocol):
    """Durable storage boundary for the local owner and browser sessions."""

    def get_owner(self) -> OwnerCredential | None: ...
    def save_owner(self, credential: OwnerCredential) -> OwnerCredential: ...
    def bootstrap_owner(
        self, credential: OwnerCredential, token_hash: str, consumed_at: datetime
    ) -> bool: ...
    def recover_owner(
        self,
        credential: OwnerCredential,
        token_hash: str,
        consumed_at: datetime,
    ) -> bool: ...
    def change_password(
        self,
        credential: OwnerCredential,
        keep_session_id: str,
        expected_password_hash: str,
        changed_at: datetime,
    ) -> bool: ...
    def get_session_by_hash(self, token_hash: str) -> BrowserSession | None: ...
    def save_session(
        self, session: BrowserSession, *, previous_token_hash: str | None = None
    ) -> BrowserSession: ...
    def revoke_session(self, session_id: str, revoked_at: datetime) -> None: ...
    def revoke_other_sessions(
        self, owner_id: str, keep_session_id: str, revoked_at: datetime
    ) -> None: ...
    def revoke_all_sessions(self, owner_id: str, revoked_at: datetime) -> None: ...
    def save_one_time_credential(self, credential: OneTimeCredential) -> OneTimeCredential: ...
    def consume_one_time_credential(
        self,
        token_hash: str,
        purpose: OneTimeCredentialPurpose,
        consumed_at: datetime,
    ) -> OneTimeCredential | None: ...


class AuditEventRepository(Protocol):
    def append(self, event: AuditEvent) -> AuditEvent: ...


class AutomationWriteRepository(Protocol):
    """Atomically upsert an automation-owned record and its required audit event."""

    def upsert_record_with_audit(
        self,
        record: Record,
        *,
        actor_id: str,
        audit_event_id: str,
    ) -> Record: ...
