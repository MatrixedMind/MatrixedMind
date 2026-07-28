from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.adapters.mongo.connection import MongoConnection
from app.adapters.mongo.repository import MongoRecordRepository
from app.adapters.mongo.security import MongoAuditEventRepository, MongoLlmTokenRepository
from app.domain.ports import AuditEventRepository, LlmTokenRepository, RecordRepository


def _build_record_repository() -> RecordRepository:
    db = MongoConnection.get_db()
    return MongoRecordRepository(db)


@lru_cache(maxsize=1)
def _get_cached_record_repository() -> RecordRepository:
    return _build_record_repository()


def get_record_repository() -> RecordRepository:
    return _get_cached_record_repository()


RecordRepoDep = Annotated[RecordRepository, Depends(get_record_repository)]


@lru_cache(maxsize=1)
def get_llm_token_repository() -> LlmTokenRepository:
    return MongoLlmTokenRepository(MongoConnection.get_db())


@lru_cache(maxsize=1)
def get_audit_event_repository() -> AuditEventRepository:
    return MongoAuditEventRepository(MongoConnection.get_db())


LlmTokenRepoDep = Annotated[LlmTokenRepository, Depends(get_llm_token_repository)]
AuditEventRepoDep = Annotated[AuditEventRepository, Depends(get_audit_event_repository)]
