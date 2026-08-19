from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING
from pymongo.client_session import ClientSession
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.adapters.mongo.security import MongoAuditEventRepository
from app.domain.models import AuditEvent, Record, RecordRevision
from app.domain.ports import AutomationWriteRepository


class MongoRecordRepository:
    def __init__(self, db: Database[dict[str, Any]], *, ensure_indexes: bool = True):
        self.collection = db.records
        if ensure_indexes:
            self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.collection.create_index(
            [("owner_id", ASCENDING), ("space", ASCENDING), ("slug", ASCENDING)],
            unique=True,
            name="records_owner_space_slug_unique",
        )
        self.collection.create_index(
            [("owner_id", ASCENDING), ("space", ASCENDING), ("parent_id", ASCENDING)],
            name="records_owner_space_parent_idx",
        )

    def get_by_slug(self, owner_id: str, space: str, slug: str) -> Record | None:
        doc = self._find_by_slug(owner_id, space, slug)
        if doc:
            return self._record_from_doc(doc)
        return None

    def list_children(self, owner_id: str, space: str, parent_id: str | None) -> list[Record]:
        query = {"owner_id": owner_id, "space": space, "parent_id": parent_id}
        docs = self.collection.find(query).sort([("created_at", ASCENDING), ("_id", ASCENDING)])
        return [self._record_from_doc(doc) for doc in docs]

    def create(self, record: Record) -> Record:
        return self._create(record)

    def _create(self, record: Record, session: ClientSession | None = None) -> Record:
        data = record.model_dump(by_alias=True, exclude={"id"})
        try:
            if session is None:
                result = self.collection.insert_one(data)
            else:
                result = self.collection.insert_one(data, session=session)
        except DuplicateKeyError as exc:
            raise ValueError(
                "record already exists for "
                f"owner_id={record.owner_id!r} space={record.space!r} slug={record.slug!r}"
            ) from exc
        return self._get_by_id(result.inserted_id, session=session)

    def update(self, owner_id: str, record_id: str, record: Record, actor_id: str) -> Record:
        return self._update(owner_id, record_id, record, actor_id, session=None)

    def _update(
        self,
        owner_id: str,
        record_id: str,
        record: Record,
        actor_id: str,
        session: ClientSession | None,
    ) -> Record:
        try:
            object_id = ObjectId(record_id)
        except InvalidId as exc:
            raise KeyError(f"record not found: {record_id}") from exc

        query = {"_id": object_id, "owner_id": owner_id}
        if session is None:
            existing_doc = self.collection.find_one(query)
        else:
            existing_doc = self.collection.find_one(query, session=session)
        if existing_doc is None:
            raise KeyError(f"record not found: {record_id}")
        if record.owner_id != owner_id:
            raise ValueError("record owner_id cannot change during update")

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
        record.created_by = existing.created_by
        record.updated_at = now
        record.updated_by = actor_id
        record.revisions = [*existing.revisions, revision]
        data = record.model_dump(by_alias=True, exclude={"id"})

        try:
            if session is None:
                result = self.collection.update_one(query, {"$set": data})
            else:
                result = self.collection.update_one(query, {"$set": data}, session=session)
        except DuplicateKeyError as exc:
            raise ValueError(
                "record already exists for "
                f"owner_id={record.owner_id!r} space={record.space!r} slug={record.slug!r}"
            ) from exc

        if result.matched_count == 0:
            raise KeyError(f"record not found: {record_id}")
        return self._get_by_id(object_id, owner_id, session=session)

    @staticmethod
    def _record_from_doc(doc: dict[str, Any]) -> Record:
        data = dict(doc)
        data["_id"] = str(data["_id"])
        return Record(**data)

    def _find_by_slug(
        self,
        owner_id: str,
        space: str,
        slug: str,
        session: ClientSession | None = None,
    ) -> dict[str, Any] | None:
        query = {"owner_id": owner_id, "space": space, "slug": slug}
        if session is None:
            return self.collection.find_one(query)
        return self.collection.find_one(query, session=session)

    def _get_by_id(
        self,
        object_id: ObjectId,
        owner_id: str | None = None,
        session: ClientSession | None = None,
    ) -> Record:
        query: dict[str, Any] = {"_id": object_id}
        if owner_id is not None:
            query["owner_id"] = owner_id
        if session is None:
            doc = self.collection.find_one(query)
        else:
            doc = self.collection.find_one(query, session=session)
        if doc is None:
            raise KeyError(f"record not found: {object_id}")
        return self._record_from_doc(doc)


class MongoAutomationWriteRepository(AutomationWriteRepository):
    def __init__(self, db: Database[dict[str, Any]], *, ensure_indexes: bool = True) -> None:
        self.db = db
        self.records = MongoRecordRepository(db, ensure_indexes=ensure_indexes)
        self.audits = MongoAuditEventRepository(db, ensure_indexes=ensure_indexes)

    def upsert_record_with_audit(
        self,
        record: Record,
        *,
        actor_id: str,
        audit_event_id: str,
    ) -> Record:
        with self.db.client.start_session() as session:
            session.start_transaction()
            try:
                existing_doc = self.records._find_by_slug(
                    record.owner_id,
                    record.space,
                    record.slug,
                    session=session,
                )
                if existing_doc is None:
                    saved = self.records._create(record, session=session)
                    action = "record.created"
                else:
                    existing = self.records._record_from_doc(existing_doc)
                    if existing.id is None:
                        raise ValueError("record has no stable identifier")
                    saved = self.records._update(
                        record.owner_id,
                        existing.id,
                        record,
                        actor_id,
                        session,
                    )
                    action = "record.updated"

                event = AuditEvent(
                    id=audit_event_id,
                    actor_id=actor_id,
                    action=action,
                    target_type="record",
                    target_id=saved.id or f"{saved.space}/{saved.slug}",
                    details={"space": saved.space, "slug": saved.slug, "source": "llm_api"},
                )
                self.audits.collection.insert_one(event.model_dump(), session=session)
            except Exception:
                session.abort_transaction()
                raise
            session.commit_transaction()
        return saved
