from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.schemas.llm import LlmRecordUpsert
from app.api.schemas.records import RecordResponse
from app.auth.dependencies import authenticate_personal_access_token
from app.dependencies import AutomationWriteRepoDep, PersonalAccessTokenRepoDep, RecordRepoDep
from app.domain.models import Record, RecordRevision

router = APIRouter(prefix="/llm", tags=["llm"])


def require_space(token_spaces: frozenset[str], space: str) -> None:
    if space not in token_spaces:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Space access denied")


@router.post(
    "/records/upsert",
    response_model=RecordResponse,
    operation_id="upsertPrivateDraftRecord",
    summary="Create or update a private draft record",
    description=(
        "Creates or updates a record in a token-authorized space. The record is always "
        "saved as a private draft with indexing disabled."
    ),
)
def upsert_record(
    request: Request,
    record_in: LlmRecordUpsert,
    token_repo: PersonalAccessTokenRepoDep,
    automation_repo: AutomationWriteRepoDep,
) -> Record:
    token = authenticate_personal_access_token(request, token_repo, "records:write")
    require_space(token.allowed_spaces, record_in.space)
    now = datetime.now(UTC)
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
    return automation_repo.upsert_record_with_audit(
        record,
        actor_id=token.actor_id,
        audit_event_id=str(uuid4()),
    )


@router.get(
    "/records/{space}/{slug}",
    response_model=RecordResponse,
    operation_id="getPrivateDraftRecord",
    summary="Get a record by space and slug",
)
def get_record(
    request: Request,
    space: str,
    slug: str,
    repo: RecordRepoDep,
    token_repo: PersonalAccessTokenRepoDep,
) -> Record:
    token = authenticate_personal_access_token(request, token_repo, "records:read")
    require_space(token.allowed_spaces, space)
    record = repo.get_by_slug(token.owner_id, space, slug)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.get(
    "/records",
    response_model=list[RecordResponse],
    operation_id="listPrivateDraftRecords",
    summary="List records in an authorized space",
)
def list_records(
    request: Request,
    repo: RecordRepoDep,
    token_repo: PersonalAccessTokenRepoDep,
    space: str = Query(...),
    parent_id: str | None = None,
) -> list[Record]:
    token = authenticate_personal_access_token(request, token_repo, "records:read")
    require_space(token.allowed_spaces, space)
    return repo.list_children(token.owner_id, space, parent_id)
