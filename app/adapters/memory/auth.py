from __future__ import annotations

from datetime import datetime
from threading import RLock

from app.domain.models import (
    BrowserSession,
    OneTimeCredential,
    OneTimeCredentialPurpose,
    OwnerCredential,
)


class InMemoryTestOwnerAuthRepository:
    """Process-local owner-auth repository for tests and contract verification only."""

    def __init__(self) -> None:
        self._owner: OwnerCredential | None = None
        self._sessions: dict[str, BrowserSession] = {}
        self._session_ids_by_hash: dict[str, str] = {}
        self._one_time_credentials: dict[str, OneTimeCredential] = {}
        self._one_time_ids_by_hash: dict[str, str] = {}
        self._lock = RLock()

    def get_owner(self) -> OwnerCredential | None:
        with self._lock:
            return self._owner.model_copy(deep=True) if self._owner else None

    def save_owner(self, credential: OwnerCredential) -> OwnerCredential:
        with self._lock:
            if self._owner is not None and self._owner.owner_id != credential.owner_id:
                raise ValueError("an owner credential already exists")
            self._owner = credential.model_copy(deep=True)
            return credential.model_copy(deep=True)

    def bootstrap_owner(
        self, credential: OwnerCredential, token_hash: str, consumed_at: datetime
    ) -> bool:
        with self._lock:
            if self._owner is not None:
                return False
            one_time = self._consume_one_time_credential(token_hash, "bootstrap", consumed_at)
            if one_time is None:
                return False
            self._owner = credential.model_copy(deep=True)
            return True

    def recover_owner(
        self,
        credential: OwnerCredential,
        token_hash: str,
        consumed_at: datetime,
    ) -> bool:
        with self._lock:
            if self._owner is None or self._owner.owner_id != credential.owner_id:
                return False
            one_time = self._consume_one_time_credential(token_hash, "recovery", consumed_at)
            if one_time is None:
                return False
            self._owner = credential.model_copy(deep=True)
            self._revoke_all_sessions(credential.owner_id, consumed_at)
            return True

    def change_password(
        self,
        credential: OwnerCredential,
        keep_session_id: str,
        expected_password_hash: str,
        changed_at: datetime,
    ) -> bool:
        with self._lock:
            keep_session = self._sessions.get(keep_session_id)
            if (
                self._owner is None
                or self._owner.owner_id != credential.owner_id
                or self._owner.password_hash != expected_password_hash
                or keep_session is None
                or keep_session.owner_id != credential.owner_id
                or keep_session.revoked_at is not None
            ):
                return False
            self._owner = credential.model_copy(deep=True)
            self._revoke_other_sessions(credential.owner_id, keep_session_id, changed_at)
            return True

    def get_session_by_hash(self, token_hash: str) -> BrowserSession | None:
        with self._lock:
            session_id = self._session_ids_by_hash.get(token_hash)
            if session_id is None:
                return None
            return self._sessions[session_id].model_copy(deep=True)

    def save_session(
        self, session: BrowserSession, *, previous_token_hash: str | None = None
    ) -> BrowserSession:
        with self._lock:
            existing_id = self._session_ids_by_hash.get(session.token_hash)
            if existing_id is not None and existing_id != session.id:
                raise ValueError("session token hash already exists")
            previous = self._sessions.get(session.id)
            if previous_token_hash is not None and (
                previous is None
                or previous.token_hash != previous_token_hash
                or previous.revoked_at is not None
            ):
                raise RuntimeError("browser session changed concurrently")
            if previous is not None and previous.token_hash != session.token_hash:
                self._session_ids_by_hash.pop(previous.token_hash, None)
            if previous is not None and previous.revoked_at is not None:
                session = session.model_copy(update={"revoked_at": previous.revoked_at})
            self._sessions[session.id] = session.model_copy(deep=True)
            self._session_ids_by_hash[session.token_hash] = session.id
            return session.model_copy(deep=True)

    def revoke_session(self, session_id: str, revoked_at: datetime) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None and session.revoked_at is None:
                self._sessions[session_id] = session.model_copy(update={"revoked_at": revoked_at})

    def revoke_other_sessions(
        self, owner_id: str, keep_session_id: str, revoked_at: datetime
    ) -> None:
        with self._lock:
            self._revoke_other_sessions(owner_id, keep_session_id, revoked_at)

    def _revoke_other_sessions(
        self, owner_id: str, keep_session_id: str, revoked_at: datetime
    ) -> None:
        for session_id, session in tuple(self._sessions.items()):
            if (
                session.owner_id == owner_id
                and session_id != keep_session_id
                and session.revoked_at is None
            ):
                self._sessions[session_id] = session.model_copy(update={"revoked_at": revoked_at})

    def revoke_all_sessions(self, owner_id: str, revoked_at: datetime) -> None:
        with self._lock:
            self._revoke_all_sessions(owner_id, revoked_at)

    def _revoke_all_sessions(self, owner_id: str, revoked_at: datetime) -> None:
        for session_id, session in tuple(self._sessions.items()):
            if session.owner_id == owner_id and session.revoked_at is None:
                self._sessions[session_id] = session.model_copy(update={"revoked_at": revoked_at})

    def save_one_time_credential(self, credential: OneTimeCredential) -> OneTimeCredential:
        with self._lock:
            existing_id = self._one_time_ids_by_hash.get(credential.token_hash)
            if existing_id is not None and existing_id != credential.id:
                raise ValueError("one-time credential token hash already exists")
            self._one_time_credentials[credential.id] = credential.model_copy(deep=True)
            self._one_time_ids_by_hash[credential.token_hash] = credential.id
            return credential.model_copy(deep=True)

    def consume_one_time_credential(
        self,
        token_hash: str,
        purpose: OneTimeCredentialPurpose,
        consumed_at: datetime,
    ) -> OneTimeCredential | None:
        with self._lock:
            return self._consume_one_time_credential(token_hash, purpose, consumed_at)

    def _consume_one_time_credential(
        self,
        token_hash: str,
        purpose: OneTimeCredentialPurpose,
        consumed_at: datetime,
    ) -> OneTimeCredential | None:
        credential_id = self._one_time_ids_by_hash.get(token_hash)
        if credential_id is None:
            return None
        credential = self._one_time_credentials[credential_id]
        if (
            credential.purpose != purpose
            or credential.consumed_at is not None
            or credential.expires_at <= consumed_at
        ):
            return None
        consumed = credential.model_copy(update={"consumed_at": consumed_at})
        self._one_time_credentials[credential_id] = consumed
        return consumed.model_copy(deep=True)
