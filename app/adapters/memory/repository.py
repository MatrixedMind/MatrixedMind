from app.domain.models import Record
from app.domain.ports import RecordRepository


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

    def update(self, record_id: str, record: Record) -> Record:
        for i, r in enumerate(self.records):
            if r.id == record_id:
                record.id = record_id
                self.records[i] = record
                return record
        raise KeyError(f"record not found: {record_id}")
