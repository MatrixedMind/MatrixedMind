from typing import NoReturn

from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas.records import RecordCreate, RecordResponse, RecordUpdate
from app.auth.dependencies import CurrentUserDep, require_api_csrf
from app.dependencies import RecordRepoDep
from app.domain.models import Record
from app.domain.policy import (
    next_index_after_for_create,
    next_index_after_for_update,
)

router = APIRouter(prefix="/records", tags=["records"])


def _raise_duplicate_record(space: str, slug: str) -> NoReturn:
    detail = f"Record with slug '{slug}' already exists in space '{space}'"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _raise_missing_record() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")


@router.post("/", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(
    request: Request,
    record_in: RecordCreate,
    repo: RecordRepoDep,
    user: CurrentUserDep,
) -> Record:
    require_api_csrf(request)
    existing = repo.get_by_slug(user.id, record_in.space, record_in.slug)
    if existing:
        _raise_duplicate_record(record_in.space, record_in.slug)

    record_data = record_in.model_dump()
    record_data["index_after"] = next_index_after_for_create(
        record_in.visibility,
        record_in.index_after,
    )
    record = Record(**record_data, owner_id=user.id, created_by=user.id, updated_by=user.id)
    try:
        return repo.create(record)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{space}/{slug}", response_model=RecordResponse)
def get_record(space: str, slug: str, repo: RecordRepoDep, user: CurrentUserDep) -> Record:
    record = repo.get_by_slug(user.id, space, slug)
    if not record:
        _raise_missing_record()
    return record


@router.put("/{space}/{slug}", response_model=RecordResponse)
def update_record(
    request: Request,
    space: str,
    slug: str,
    record_in: RecordUpdate,
    repo: RecordRepoDep,
    user: CurrentUserDep,
) -> Record:
    require_api_csrf(request)
    existing = repo.get_by_slug(user.id, space, slug)
    if existing is None:
        _raise_missing_record()
    if existing.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Existing record cannot be updated without an id",
        )

    update_data = record_in.model_dump(exclude_unset=True)
    if update_data.get("tags") is None:
        update_data.pop("tags", None)
    if update_data.get("index_after") is None and "index_after" not in record_in.model_fields_set:
        update_data.pop("index_after", None)

    next_space = update_data.get("space", existing.space)
    next_slug = update_data.get("slug", existing.slug)
    duplicate = repo.get_by_slug(user.id, next_space, next_slug)
    if duplicate is not None and duplicate.id != existing.id:
        _raise_duplicate_record(next_space, next_slug)

    next_visibility = update_data.get("visibility", existing.visibility)
    update_data["index_after"] = next_index_after_for_update(
        current_visibility=existing.visibility,
        next_visibility=next_visibility,
        index_after=update_data.get("index_after", existing.index_after),
        index_after_was_provided="index_after" in record_in.model_fields_set,
    )

    updated = existing.model_copy(update=update_data)
    try:
        return repo.update(user.id, existing.id, updated, actor_id=user.id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{space}", response_model=list[RecordResponse])
def list_records(
    space: str,
    repo: RecordRepoDep,
    user: CurrentUserDep,
    parent_id: str | None = None,
) -> list[Record]:
    return [record for record in repo.list_children(user.id, space, parent_id)]
