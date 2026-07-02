from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.records import RecordCreate, RecordResponse, RecordUpdate
from app.dependencies import RecordRepoDep
from app.domain.models import Record

router = APIRouter(prefix="/records", tags=["records"])


def _raise_duplicate_record(space: str, slug: str) -> NoReturn:
    detail = f"Record with slug '{slug}' already exists in space '{space}'"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _raise_missing_record() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")


@router.post("/", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(record_in: RecordCreate, repo: RecordRepoDep) -> Record:
    existing = repo.get_by_slug(record_in.space, record_in.slug)
    if existing:
        _raise_duplicate_record(record_in.space, record_in.slug)

    record = Record(**record_in.model_dump())
    try:
        return repo.create(record)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{space}/{slug}", response_model=RecordResponse)
def get_record(space: str, slug: str, repo: RecordRepoDep) -> Record:
    record = repo.get_by_slug(space, slug)
    if not record:
        _raise_missing_record()
    return record


@router.put("/{space}/{slug}", response_model=RecordResponse)
def update_record(
    space: str,
    slug: str,
    record_in: RecordUpdate,
    repo: RecordRepoDep,
) -> Record:
    existing = repo.get_by_slug(space, slug)
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

    next_space = update_data.get("space", existing.space)
    next_slug = update_data.get("slug", existing.slug)
    duplicate = repo.get_by_slug(next_space, next_slug)
    if duplicate is not None and duplicate.id != existing.id:
        _raise_duplicate_record(next_space, next_slug)

    updated = existing.model_copy(update=update_data)
    try:
        return repo.update(existing.id, updated)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{space}", response_model=list[RecordResponse])
def list_records(space: str, repo: RecordRepoDep, parent_id: str | None = None) -> list[Record]:
    return repo.list_children(space, parent_id)
