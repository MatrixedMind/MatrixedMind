from fastapi import APIRouter, HTTPException, status

from app.api.schemas.records import RecordCreate, RecordResponse
from app.dependencies import RecordRepoDep
from app.domain.models import Record

router = APIRouter(prefix="/records", tags=["records"])


@router.post("/", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(record_in: RecordCreate, repo: RecordRepoDep) -> Record:
    # Check if slug already exists in space
    existing = repo.get_by_slug(record_in.space, record_in.slug)
    if existing:
        detail = f"Record with slug '{record_in.slug}' already exists in space '{record_in.space}'"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    record = Record(**record_in.model_dump())
    return repo.create(record)


@router.get("/{space}/{slug}", response_model=RecordResponse)
async def get_record(space: str, slug: str, repo: RecordRepoDep) -> Record:
    record = repo.get_by_slug(space, slug)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record


@router.get("/{space}", response_model=list[RecordResponse])
async def list_records(
    space: str, repo: RecordRepoDep, parent_id: str | None = None
) -> list[Record]:
    return repo.list_children(space, parent_id)
