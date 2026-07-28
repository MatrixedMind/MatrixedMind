from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.domain.models import Record, RecordRevision


class MongoRecordRepository:
    def __init__(self, db: Database[dict[str, Any]]):
        self.collection = db.records
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.collection.create_index(
            [("space", ASCENDING), ("slug", ASCENDING)],
            unique=True,
            name="records_space_slug_unique",
        )
        self.collection.create_index(
            [("space", ASCENDING), ("parent_id", ASCENDING)],
            name="records_space_parent_idx",
        )

    def get_by_slug(self, space: str, slug: str) -> Record | None:
        doc = self.collection.find_one({"space": space, "slug": slug})
        if doc:
            return self._record_from_doc(doc)
        return None

    def list_children(self, space: str, parent_id: str | None) -> list[Record]:
        query = {"space": space, "parent_id": parent_id}
        docs = self.collection.find(query).sort([("created_at", ASCENDING), ("_id", ASCENDING)])
        return [self._record_from_doc(doc) for doc in docs]

    def create(self, record: Record) -> Record:
        data = record.model_dump(by_alias=True, exclude={"id"})
        try:
            result = self.collection.insert_one(data)
        except DuplicateKeyError as exc:
            raise ValueError(
                f"record already exists for space={record.space!r} slug={record.slug!r}"
            ) from exc
        return self._get_by_id(result.inserted_id)

    def update(self, record_id: str, record: Record, actor_id: str = "system") -> Record:
        try:
            object_id = ObjectId(record_id)
        except InvalidId as exc:
            raise KeyError(f"record not found: {record_id}") from exc

        existing_doc = self.collection.find_one({"_id": object_id})
        if existing_doc is None:
            raise KeyError(f"record not found: {record_id}")

        existing = self._record_from_doc(existing_doc)
        now = datetime.now(UTC)
        revision = RecordRevision(
            revision_id=str(ObjectId()),
            author_id=existing.updated_by,
            timestamp=now,
            body_markdown=existing.body_markdown,
        )

        record.id = record_id
        record.created_at = existing.created_at
        record.updated_at = now
        record.updated_by = actor_id
        record.revisions = [*existing.revisions, revision]
        data = record.model_dump(by_alias=True, exclude={"id"})

        try:
            result = self.collection.update_one({"_id": object_id}, {"$set": data})
        except DuplicateKeyError as exc:
            raise ValueError(
                f"record already exists for space={record.space!r} slug={record.slug!r}"
            ) from exc

        if result.matched_count == 0:
            raise KeyError(f"record not found: {record_id}")
        return self._get_by_id(object_id)

    @staticmethod
    def _record_from_doc(doc: dict[str, Any]) -> Record:
        data = dict(doc)
        data["_id"] = str(data["_id"])
        return Record(**data)

    def _get_by_id(self, object_id: ObjectId) -> Record:
        doc = self.collection.find_one({"_id": object_id})
        if doc is None:
            raise KeyError(f"record not found: {object_id}")
        return self._record_from_doc(doc)
