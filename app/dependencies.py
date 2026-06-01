from typing import Annotated

from fastapi import Depends

from app.adapters.mongo.connection import MongoConnection
from app.adapters.mongo.repository import MongoRecordRepository
from app.domain.ports import RecordRepository


def get_record_repository() -> RecordRepository:
    db = MongoConnection.get_db()
    return MongoRecordRepository(db)


RecordRepoDep = Annotated[RecordRepository, Depends(get_record_repository)]
