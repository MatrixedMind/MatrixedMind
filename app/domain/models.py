from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class RecordRevision(BaseModel):
    revision_id: str
    author_id: str
    timestamp: datetime
    body_markdown: str


class Record(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(None, alias="_id")
    space: str
    slug: str
    title: str
    body_markdown: str
    tags: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revisions: list[RecordRevision] = []
