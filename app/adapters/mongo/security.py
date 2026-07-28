from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING
from pymongo.database import Database

from app.domain.models import AuditEvent, LlmApiToken


class MongoLlmTokenRepository:
    def __init__(self, db: Database[dict[str, Any]]):
        self.collection = db.llm_api_tokens
        self.collection.create_index([("token_hash", ASCENDING)], unique=True)

    def get_by_hash(self, token_hash: str) -> LlmApiToken | None:
        document = self.collection.find_one({"token_hash": token_hash})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return LlmApiToken(**document)

    def save(self, token: LlmApiToken) -> LlmApiToken:
        data = token.model_dump(exclude={"id"})
        data["scopes"] = list(token.scopes)
        data["allowed_spaces"] = list(token.allowed_spaces)
        self.collection.update_one({"_id": token.id}, {"$set": data}, upsert=True)
        return token

    def revoke(self, token_id: str) -> None:
        result = self.collection.update_one(
            {"_id": token_id},
            {"$set": {"revoked_at": datetime.now(UTC)}},
        )
        if result.matched_count == 0:
            raise KeyError(f"token not found: {token_id}")


class MongoAuditEventRepository:
    def __init__(self, db: Database[dict[str, Any]]):
        self.collection = db.audit_events
        self.collection.create_index([("timestamp", ASCENDING)])
        self.collection.create_index([("target_type", ASCENDING), ("target_id", ASCENDING)])

    def append(self, event: AuditEvent) -> AuditEvent:
        self.collection.insert_one(event.model_dump())
        return event
