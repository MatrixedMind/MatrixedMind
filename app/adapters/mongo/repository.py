from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database

from app.domain.models import Record


class MongoRecordRepository:
    def __init__(self, db: Database[dict[str, Any]]):
        self.collection = db.records

    def get_by_slug(self, space: str, slug: str) -> Record | None:
        doc = self.collection.find_one({"space": space, "slug": slug})
        if doc:
            doc["_id"] = str(doc["_id"])
            return Record(**doc)
        return None

    def list_children(self, space: str, parent_id: str | None) -> list[Record]:
        query = {"space": space, "parent_id": parent_id}
        docs = self.collection.find(query)
        records = []
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            records.append(Record(**doc))
        return records

    def create(self, record: Record) -> Record:
        data = record.model_dump(by_alias=True, exclude={"id"})
        result = self.collection.insert_one(data)
        record.id = str(result.inserted_id)
        return record

    def update(self, record_id: str, record: Record) -> Record:
        data = record.model_dump(by_alias=True, exclude={"id"})
        try:
            object_id = ObjectId(record_id)
        except InvalidId as exc:
            raise KeyError(f"record not found: {record_id}") from exc

        result = self.collection.update_one({"_id": object_id}, {"$set": data})
        if result.matched_count == 0:
            raise KeyError(f"record not found: {record_id}")
        record.id = record_id
        return record
