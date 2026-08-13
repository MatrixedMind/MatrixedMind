from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.domain.models import AuditEvent, PersonalAccessToken


class MongoPersonalAccessTokenRepository:
    def __init__(self, db: Database[dict[str, Any]], *, ensure_indexes: bool = True):
        self.collection = db.llm_api_tokens
        if ensure_indexes:
            self.collection.create_index(
                [("token_hash", ASCENDING)], unique=True, name="llm_api_tokens_token_hash_unique"
            )

    def get_by_hash(self, token_hash: str) -> PersonalAccessToken | None:
        document = self.collection.find_one({"token_hash": token_hash})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return PersonalAccessToken(**document)

    def save(self, token: PersonalAccessToken) -> PersonalAccessToken:
        data = token.model_dump(exclude={"id"})
        data["scopes"] = list(token.scopes)
        data["allowed_spaces"] = list(token.allowed_spaces)
        revoked_at = data.pop("revoked_at")
        update: dict[str, Any] = {
            "$set": data,
            "$setOnInsert": {"revoked_at": revoked_at},
        }
        try:
            self.collection.update_one({"_id": token.id}, update, upsert=True)
            if revoked_at is not None:
                self.collection.update_one(
                    {"_id": token.id, "revoked_at": None},
                    {"$set": {"revoked_at": revoked_at}},
                )
        except DuplicateKeyError as exc:
            raise ValueError(f"token hash already exists: {token.token_hash}") from exc
        stored = self.collection.find_one({"_id": token.id})
        if stored is None:
            raise KeyError(f"token not found after save: {token.id}")
        stored["id"] = str(stored.pop("_id"))
        return PersonalAccessToken(**stored)

    def revoke(self, token_id: str) -> None:
        token = self.collection.find_one({"_id": token_id}, {"revoked_at": 1})
        if token is None:
            raise KeyError(f"token not found: {token_id}")
        if token.get("revoked_at") is None:
            self.collection.update_one(
                {"_id": token_id, "revoked_at": None},
                {"$set": {"revoked_at": datetime.now(UTC)}},
            )


class MongoAuditEventRepository:
    def __init__(self, db: Database[dict[str, Any]], *, ensure_indexes: bool = True):
        self.collection = db.audit_events
        if ensure_indexes:
            self.collection.create_index([("timestamp", ASCENDING)])
            self.collection.create_index([("target_type", ASCENDING), ("target_id", ASCENDING)])

    def append(self, event: AuditEvent) -> AuditEvent:
        self.collection.insert_one(event.model_dump())
        return event
