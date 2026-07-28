from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.policy import RecordVisibility
from app.domain.validation import (
    validate_markdown,
    validate_path,
    validate_slug,
    validate_title,
)


class RecordCreate(BaseModel):
    space: str
    slug: str
    parent_id: str | None = None
    path: str | None = None
    title: str
    body_markdown: str
    tags: list[str] = Field(default_factory=list)
    visibility: RecordVisibility = "private"
    index_after: datetime | None = None

    @field_validator("space", "slug")
    @staticmethod
    def validate_record_slug(value: str) -> str:
        return validate_slug(value)

    @field_validator("parent_id")
    @staticmethod
    def validate_parent_id(value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identifier must not be empty")
        return value

    @field_validator("path")
    @staticmethod
    def validate_record_path(value: str | None) -> str | None:
        if value is None:
            return value
        return validate_path(value)

    @field_validator("title")
    @staticmethod
    def validate_record_title(value: str) -> str:
        return validate_title(value)

    @field_validator("body_markdown")
    @staticmethod
    def validate_record_markdown(value: str) -> str:
        return validate_markdown(value)

    @field_validator("tags")
    @staticmethod
    def validate_record_tags(value: list[str]) -> list[str]:
        return [validate_slug(tag) for tag in value]


class RecordUpdate(BaseModel):
    space: str | None = None
    slug: str | None = None
    parent_id: str | None = None
    path: str | None = None
    title: str | None = None
    body_markdown: str | None = None
    tags: list[str] | None = None
    visibility: RecordVisibility | None = None
    index_after: datetime | None = None

    @model_validator(mode="after")
    def validate_has_update(self) -> "RecordUpdate":
        if not self.model_fields_set:
            raise ValueError("update payload must include at least one field")

        non_nullable_fields = ("space", "slug", "title", "body_markdown", "visibility")
        for field_name in non_nullable_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")

        return self

    @field_validator("space", "slug")
    @staticmethod
    def validate_record_slug(value: str | None) -> str | None:
        if value is None:
            return value
        return validate_slug(value)

    @field_validator("parent_id")
    @staticmethod
    def validate_parent_id(value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identifier must not be empty")
        return value

    @field_validator("path")
    @staticmethod
    def validate_record_path(value: str | None) -> str | None:
        if value is None:
            return value
        return validate_path(value)

    @field_validator("title")
    @staticmethod
    def validate_record_title(value: str | None) -> str | None:
        if value is None:
            return value
        return validate_title(value)

    @field_validator("body_markdown")
    @staticmethod
    def validate_record_markdown(value: str | None) -> str | None:
        if value is None:
            return value
        return validate_markdown(value)

    @field_validator("tags")
    @staticmethod
    def validate_record_tags(value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return [validate_slug(tag) for tag in value]


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parent_id: str | None
    space: str
    slug: str
    path: str | None
    title: str
    body_markdown: str
    tags: list[str]
    visibility: RecordVisibility
    draft: bool
    index_after: datetime | None
    owner_id: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
