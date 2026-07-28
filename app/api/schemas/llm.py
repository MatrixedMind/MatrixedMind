from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.validation import validate_markdown, validate_path, validate_slug, validate_title


class LlmRecordUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    space: str
    slug: str
    title: str
    body_markdown: str
    parent_id: str | None = None
    path: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("space", "slug")
    @staticmethod
    def validate_slug_field(value: str) -> str:
        return validate_slug(value)

    @field_validator("title")
    @staticmethod
    def validate_title_field(value: str) -> str:
        return validate_title(value)

    @field_validator("body_markdown")
    @staticmethod
    def validate_body(value: str) -> str:
        return validate_markdown(value)

    @field_validator("path")
    @staticmethod
    def validate_path_field(value: str | None) -> str | None:
        return validate_path(value) if value is not None else None

    @field_validator("tags")
    @staticmethod
    def validate_tags(value: list[str]) -> list[str]:
        return [validate_slug(tag) for tag in value]
