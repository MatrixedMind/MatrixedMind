from pydantic import BaseModel, ConfigDict, Field


class RecordCreate(BaseModel):
    space: str
    slug: str
    title: str
    body_markdown: str
    tags: list[str] = Field(default_factory=list)


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space: str
    slug: str
    title: str
    body_markdown: str
    tags: list[str]
