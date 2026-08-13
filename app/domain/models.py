from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    draft: bool = True
    index_after: datetime | None = None
    owner_id: str
    created_by: str = "system"
    updated_by: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revisions: list[RecordRevision] = Field(default_factory=list)

    @field_validator("id", "parent_id")
    @staticmethod
    def validate_optional_identifier(value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identifier must not be empty")
        return value

    @field_validator("owner_id", "created_by", "updated_by")
    @staticmethod
    def validate_actor_identifier(value: str) -> str:
        if not value.strip():
            raise ValueError("actor identifier must not be empty")
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
    principal_type: Literal["user"] = "user"

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


class OwnerCredential(BaseModel):
    owner_id: str
    display_name: str
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    password_changed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("owner_id", "password_hash")
    @classmethod
    def validate_required_value(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("credential value must not be empty")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_owner_display_name(cls, value: str) -> str:
        return validate_title(value)


class BrowserSession(BaseModel):
    id: str
    owner_id: str
    token_hash: str
    csrf_token_hash: str
    created_at: datetime
    last_seen_at: datetime
    rotated_at: datetime
    absolute_expires_at: datetime
    revoked_at: datetime | None = None

    @field_validator("id", "owner_id", "token_hash", "csrf_token_hash")
    @classmethod
    def validate_session_value(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("session value must not be empty")
        return value

    @model_validator(mode="after")
    def validate_session_timeline(self) -> "BrowserSession":
        if self.last_seen_at < self.created_at or self.rotated_at < self.created_at:
            raise ValueError("session activity cannot precede creation")
        if self.absolute_expires_at <= self.created_at:
            raise ValueError("session expiration must follow creation")
        return self


OneTimeCredentialPurpose = Literal["bootstrap", "recovery"]


class OneTimeCredential(BaseModel):
    id: str
    purpose: OneTimeCredentialPurpose
    token_hash: str
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None

    @field_validator("id", "token_hash")
    @classmethod
    def validate_one_time_value(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("one-time credential value must not be empty")
        return value

    @model_validator(mode="after")
    def validate_one_time_timeline(self) -> "OneTimeCredential":
        if self.expires_at <= self.created_at:
            raise ValueError("one-time credential expiration must follow creation")
        if self.consumed_at is not None and self.consumed_at < self.created_at:
            raise ValueError("one-time credential consumption cannot precede creation")
        return self


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


PersonalAccessTokenScope = Literal["records:read", "records:write"]


class PersonalAccessToken(BaseModel):
    id: str
    name: str
    token_hash: str
    scopes: frozenset[PersonalAccessTokenScope]
    allowed_spaces: frozenset[str]
    owner_id: str
    actor_id: str
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("id", "name", "token_hash", "actor_id", "owner_id")
    @staticmethod
    def validate_token_text(value: str) -> str:
        if not value.strip():
            raise ValueError("token value must not be empty")
        return value

    @field_validator("allowed_spaces")
    @classmethod
    def validate_allowed_spaces(cls, value: frozenset[str]) -> frozenset[str]:
        if not value:
            raise ValueError("at least one allowed space is required")
        return frozenset(validate_slug(space) for space in value)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None


class AuditEvent(BaseModel):
    id: str
    actor_id: str
    action: str
    target_type: str
    target_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, str] = Field(default_factory=dict)
