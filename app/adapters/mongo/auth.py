from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.domain.models import (
    BrowserSession,
    OneTimeCredential,
    OneTimeCredentialPurpose,
    OwnerCredential,
)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class MongoOwnerAuthRepository:
    """MongoDB persistence for local owner credentials and opaque sessions."""

    def __init__(self, db: Database[dict[str, Any]], *, ensure_indexes: bool = True) -> None:
        self._owners = db["owner_credentials"]
        self._sessions = db["browser_sessions"]
        self._one_time = db["owner_one_time_credentials"]
        if ensure_indexes:
            self._sessions.create_index([("token_hash", ASCENDING)], unique=True)
            self._sessions.create_index([("owner_id", ASCENDING), ("revoked_at", ASCENDING)])
            self._one_time.create_index([("token_hash", ASCENDING)], unique=True)
            self._one_time.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)

    def get_owner(self) -> OwnerCredential | None:
        document = self._owners.find_one({})
        if document is None:
            return None
        document["owner_id"] = document.pop("_id")
        for key in ("created_at", "password_changed_at"):
            document[key] = _aware(document[key])
        return OwnerCredential.model_validate(document)

    def save_owner(self, credential: OwnerCredential) -> OwnerCredential:
        document = credential.model_dump()
        document["_id"] = document.pop("owner_id")
        existing = self._owners.find_one({}, {"_id": 1})
        if existing is not None and existing["_id"] != credential.owner_id:
            raise ValueError("an owner credential already exists")
        self._owners.replace_one({"_id": credential.owner_id}, document, upsert=True)
        return credential

    def bootstrap_owner(
        self, credential: OwnerCredential, token_hash: str, consumed_at: datetime
    ) -> bool:
        document = credential.model_dump()
        document["_id"] = document.pop("owner_id")
        try:
            with (
                self._owners.database.client.start_session() as mongo_session,
                mongo_session.start_transaction(),
            ):
                consumed = self._one_time.update_one(
                    {
                        "token_hash": token_hash,
                        "purpose": "bootstrap",
                        "consumed_at": None,
                        "expires_at": {"$gt": consumed_at},
                    },
                    {"$set": {"consumed_at": consumed_at}},
                    session=mongo_session,
                )
                if consumed.modified_count != 1:
                    mongo_session.abort_transaction()
                    return False
                try:
                    self._owners.insert_one(document, session=mongo_session)
                except DuplicateKeyError:
                    mongo_session.abort_transaction()
                    return False
        except DuplicateKeyError:
            return False
        return True

    def recover_owner(
        self,
        credential: OwnerCredential,
        token_hash: str,
        consumed_at: datetime,
    ) -> bool:
        document = credential.model_dump()
        document["_id"] = document.pop("owner_id")
        with (
            self._owners.database.client.start_session() as mongo_session,
            mongo_session.start_transaction(),
        ):
            consumed = self._one_time.update_one(
                {
                    "token_hash": token_hash,
                    "purpose": "recovery",
                    "consumed_at": None,
                    "expires_at": {"$gt": consumed_at},
                },
                {"$set": {"consumed_at": consumed_at}},
                session=mongo_session,
            )
            if consumed.modified_count != 1:
                mongo_session.abort_transaction()
                return False
            replaced = self._owners.replace_one(
                {"_id": credential.owner_id}, document, session=mongo_session
            )
            if replaced.matched_count != 1:
                mongo_session.abort_transaction()
                return False
            self._sessions.update_many(
                {"owner_id": credential.owner_id, "revoked_at": None},
                {"$set": {"revoked_at": consumed_at}},
                session=mongo_session,
            )
        return True

    def change_password(
        self,
        credential: OwnerCredential,
        keep_session_id: str,
        expected_password_hash: str,
        changed_at: datetime,
    ) -> bool:
        document = credential.model_dump()
        document["_id"] = document.pop("owner_id")
        with (
            self._owners.database.client.start_session() as mongo_session,
            mongo_session.start_transaction(),
        ):
            active_session = self._sessions.find_one(
                {
                    "_id": keep_session_id,
                    "owner_id": credential.owner_id,
                    "revoked_at": None,
                },
                {"_id": 1},
                session=mongo_session,
            )
            if active_session is None:
                mongo_session.abort_transaction()
                return False
            replaced = self._owners.replace_one(
                {"_id": credential.owner_id, "password_hash": expected_password_hash},
                document,
                session=mongo_session,
            )
            if replaced.matched_count != 1:
                mongo_session.abort_transaction()
                return False
            self._sessions.update_many(
                {
                    "owner_id": credential.owner_id,
                    "_id": {"$ne": keep_session_id},
                    "revoked_at": None,
                },
                {"$set": {"revoked_at": changed_at}},
                session=mongo_session,
            )
        return True

    def get_session_by_hash(self, token_hash: str) -> BrowserSession | None:
        document = self._sessions.find_one({"token_hash": token_hash})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        for key in (
            "created_at",
            "last_seen_at",
            "rotated_at",
            "absolute_expires_at",
            "revoked_at",
        ):
            if document.get(key) is not None:
                document[key] = _aware(document[key])
        return BrowserSession.model_validate(document)

    def save_session(
        self, session: BrowserSession, *, previous_token_hash: str | None = None
    ) -> BrowserSession:
        document = session.model_dump()
        document.pop("id")
        revoked_at = document.pop("revoked_at")
        try:
            query: dict[str, Any] = {"_id": session.id}
            if previous_token_hash is not None:
                query["token_hash"] = previous_token_hash
                query["revoked_at"] = None
            result = self._sessions.update_one(
                query,
                {"$set": document, "$setOnInsert": {"revoked_at": revoked_at}},
                upsert=previous_token_hash is None,
            )
        except DuplicateKeyError as exc:
            raise ValueError("session token hash already exists") from exc
        if previous_token_hash is not None and result.matched_count != 1:
            raise RuntimeError("browser session changed concurrently")
        persisted = self.get_session_by_hash(session.token_hash)
        if persisted is None:
            raise RuntimeError("saved session could not be read")
        return persisted

    def revoke_session(self, session_id: str, revoked_at: datetime) -> None:
        self._sessions.update_one(
            {"_id": session_id, "revoked_at": None}, {"$set": {"revoked_at": revoked_at}}
        )

    def revoke_other_sessions(
        self, owner_id: str, keep_session_id: str, revoked_at: datetime
    ) -> None:
        self._sessions.update_many(
            {"owner_id": owner_id, "_id": {"$ne": keep_session_id}, "revoked_at": None},
            {"$set": {"revoked_at": revoked_at}},
        )

    def revoke_all_sessions(self, owner_id: str, revoked_at: datetime) -> None:
        self._sessions.update_many(
            {"owner_id": owner_id, "revoked_at": None},
            {"$set": {"revoked_at": revoked_at}},
        )

    def save_one_time_credential(self, credential: OneTimeCredential) -> OneTimeCredential:
        document = credential.model_dump()
        document["_id"] = document.pop("id")
        try:
            self._one_time.insert_one(document)
        except DuplicateKeyError as exc:
            raise ValueError("one-time credential token hash already exists") from exc
        return credential

    def consume_one_time_credential(
        self,
        token_hash: str,
        purpose: OneTimeCredentialPurpose,
        consumed_at: datetime,
    ) -> OneTimeCredential | None:
        document = self._one_time.find_one_and_update(
            {
                "token_hash": token_hash,
                "purpose": purpose,
                "consumed_at": None,
                "expires_at": {"$gt": consumed_at},
            },
            {"$set": {"consumed_at": consumed_at}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        for key in ("created_at", "expires_at", "consumed_at"):
            document[key] = _aware(document[key])
        return OneTimeCredential.model_validate(document)
