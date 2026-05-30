from datetime import datetime

from pydantic import BaseModel, Field


class RecordRevision(BaseModel):
    revision_id: str
    author_id: str
    timestamp: datetime
    body_markdown: str


class Record(BaseModel):
    id: str | None = Field(None, alias="_id")
    space: str
    slug: str
    title: str
    body_markdown: str
    tags: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    revisions: list[RecordRevision] = []

    class Config:
        populate_by_name = True
