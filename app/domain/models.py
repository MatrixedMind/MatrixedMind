from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.policy import RecordVisibility
from app.domain.validation import validate_markdown, validate_path, validate_slug, validate_title


class RecordRevision(BaseModel):
    revision_id: str
    author_id: str
    timestamp: datetime
    body_markdown: str

    @field_validator("revision_id", "author_id")
    @staticmethod
    def validate_required_identifier(value: str) -> str:
        if not value.strip():
            raise ValueError("identifier must not be empty")
        return value

    @field_validator("body_markdown")
    @staticmethod
    def validate_revision_markdown(value: str) -> str:
        return validate_markdown(value)


class Record(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(None, alias="_id")
    parent_id: str | None = None
    space: str
    slug: str
    path: str | None = None
    title: str
    body_markdown: str
    tags: list[str] = Field(default_factory=list)
    visibility: RecordVisibility = "private"
    index_after: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revisions: list[RecordRevision] = Field(default_factory=list)

    @field_validator("id", "parent_id")
    @staticmethod
    def validate_optional_identifier(value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identifier must not be empty")
        return value

    @field_validator("space", "slug")
    @staticmethod
    def validate_record_slug(value: str) -> str:
        return validate_slug(value)

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


class Space(BaseModel):
    id: str | None = Field(None, alias="_id")
    slug: str
    name: str
    owner_id: str

    @field_validator("slug")
    @staticmethod
    def validate_space_slug(value: str) -> str:
        return validate_slug(value)

    @field_validator("name")
    @staticmethod
    def validate_space_name(value: str) -> str:
        return validate_title(value)

    @field_validator("owner_id")
    @staticmethod
    def validate_owner_id(value: str) -> str:
        if not value.strip():
            raise ValueError("owner_id must not be empty")
        return value


class Tag(BaseModel):
    id: str | None = Field(None, alias="_id")
    space: str
    slug: str
    label: str

    @field_validator("space", "slug")
    @staticmethod
    def validate_tag_slug(value: str) -> str:
        return validate_slug(value)

    @field_validator("label")
    @staticmethod
    def validate_tag_label(value: str) -> str:
        return validate_title(value)


class User(BaseModel):
    id: str
    display_name: str

    @field_validator("id")
    @staticmethod
    def validate_user_id(value: str) -> str:
        if not value.strip():
            raise ValueError("user id must not be empty")
        return value

    @field_validator("display_name")
    @staticmethod
    def validate_display_name(value: str) -> str:
        return validate_title(value)


class Membership(BaseModel):
    user_id: str
    space: str
    role: Literal["owner", "editor", "viewer"]

    @field_validator("user_id")
    @staticmethod
    def validate_member_user_id(value: str) -> str:
        if not value.strip():
            raise ValueError("user_id must not be empty")
        return value

    @field_validator("space")
    @staticmethod
    def validate_member_space(value: str) -> str:
        return validate_slug(value)
