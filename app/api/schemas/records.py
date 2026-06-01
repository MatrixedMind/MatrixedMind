from pydantic import BaseModel, ConfigDict


class RecordCreate(BaseModel):
    space: str
    slug: str
    title: str
    body_markdown: str
    tags: list[str] = []


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space: str
    slug: str
    title: str
    body_markdown: str
    tags: list[str]
