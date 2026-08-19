from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.adapters.mongo.connection import MongoConnection
from app.adapters.mongo.repository import MongoAutomationWriteRepository, MongoRecordRepository
from app.adapters.mongo.security import (
    MongoAuditEventRepository,
    MongoPersonalAccessTokenRepository,
)
from app.domain.ports import (
    AuditEventRepository,
    AutomationWriteRepository,
    PersonalAccessTokenRepository,
    RecordRepository,
)
from app.settings import settings


def _build_record_repository() -> RecordRepository:
    db = MongoConnection.get_db()
    return MongoRecordRepository(db, ensure_indexes=settings.mongo_ensure_indexes)


@lru_cache(maxsize=1)
def _get_cached_record_repository() -> RecordRepository:
    return _build_record_repository()


def get_record_repository() -> RecordRepository:
    return _get_cached_record_repository()


RecordRepoDep = Annotated[RecordRepository, Depends(get_record_repository)]


@lru_cache(maxsize=1)
def get_personal_access_token_repository() -> PersonalAccessTokenRepository:
    return MongoPersonalAccessTokenRepository(
        MongoConnection.get_db(), ensure_indexes=settings.mongo_ensure_indexes
    )


@lru_cache(maxsize=1)
def get_audit_event_repository() -> AuditEventRepository:
    return MongoAuditEventRepository(
        MongoConnection.get_db(), ensure_indexes=settings.mongo_ensure_indexes
    )


PersonalAccessTokenRepoDep = Annotated[
    PersonalAccessTokenRepository, Depends(get_personal_access_token_repository)
]
AuditEventRepoDep = Annotated[AuditEventRepository, Depends(get_audit_event_repository)]


@lru_cache(maxsize=1)
def get_automation_write_repository() -> AutomationWriteRepository:
    return MongoAutomationWriteRepository(
        MongoConnection.get_db(), ensure_indexes=settings.mongo_ensure_indexes
    )


AutomationWriteRepoDep = Annotated[
    AutomationWriteRepository, Depends(get_automation_write_repository)
]
