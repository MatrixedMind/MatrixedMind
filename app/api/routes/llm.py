from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.schemas.llm import LlmRecordUpsert
from app.api.schemas.records import RecordResponse
from app.auth.dependencies import authenticate_llm_token
from app.dependencies import AuditEventRepoDep, LlmTokenRepoDep, RecordRepoDep
from app.domain.models import AuditEvent, Record, RecordRevision

router = APIRouter(prefix="/llm", tags=["llm"])


def require_space(token_spaces: frozenset[str], space: str) -> None:
    if space not in token_spaces:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Space access denied")


def require_record_owner(record: Record, owner_id: str) -> None:
    if record.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")


@router.post("/records/upsert", response_model=RecordResponse)
def upsert_record(
    request: Request,
    record_in: LlmRecordUpsert,
    repo: RecordRepoDep,
    token_repo: LlmTokenRepoDep,
    audit_repo: AuditEventRepoDep,
) -> Record:
    token = authenticate_llm_token(request, token_repo, "records:write")
    require_space(token.allowed_spaces, record_in.space)
    now = datetime.now(UTC)
    existing = repo.get_by_slug(record_in.space, record_in.slug)
    if existing is None:
        revision = RecordRevision(
            revision_id=str(uuid4()),
            author_id=token.actor_id,
            timestamp=now,
            body_markdown=record_in.body_markdown,
        )
        record = Record(
            **record_in.model_dump(),
            visibility="private",
            draft=True,
            index_after=None,
            owner_id=token.owner_id,
            created_by=token.actor_id,
            updated_by=token.actor_id,
            revisions=[revision],
        )
        saved = repo.create(record)
        action = "record.created"
    else:
        require_record_owner(existing, token.owner_id)
        if existing.id is None:
            raise HTTPException(status_code=409, detail="Record has no stable identifier")
        updated = existing.model_copy(
            update={
                **record_in.model_dump(),
                "visibility": "private",
                "draft": True,
                "index_after": None,
            }
        )
        saved = repo.update(existing.id, updated, actor_id=token.actor_id)
        action = "record.updated"

    audit_repo.append(
        AuditEvent(
            id=str(uuid4()),
            actor_id=token.actor_id,
            action=action,
            target_type="record",
            target_id=saved.id or f"{saved.space}/{saved.slug}",
            details={"space": saved.space, "slug": saved.slug, "source": "llm_api"},
        )
    )
    return saved


@router.get("/records/{space}/{slug}", response_model=RecordResponse)
def get_record(
    request: Request,
    space: str,
    slug: str,
    repo: RecordRepoDep,
    token_repo: LlmTokenRepoDep,
) -> Record:
    token = authenticate_llm_token(request, token_repo, "records:read")
    require_space(token.allowed_spaces, space)
    record = repo.get_by_slug(space, slug)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    require_record_owner(record, token.owner_id)
    return record


@router.get("/records", response_model=list[RecordResponse])
def list_records(
    request: Request,
    repo: RecordRepoDep,
    token_repo: LlmTokenRepoDep,
    space: str = Query(...),
    parent_id: str | None = None,
) -> list[Record]:
    token = authenticate_llm_token(request, token_repo, "records:read")
    require_space(token.allowed_spaces, space)
    return [
        record
        for record in repo.list_children(space, parent_id)
        if record.owner_id == token.owner_id
    ]
