from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.models import (
    Membership,
    PersonalAccessToken,
    Record,
    RecordRevision,
    Space,
    Tag,
    User,
)


def test_record_validates_and_normalizes_core_fields() -> None:
    record = Record(
        space="personal",
        slug="hello-world",
        path="/personal/hello-world",
        title="  Hello World  ",
        body_markdown="# Hello",
        tags=["daily-notes"],
        owner_id="user-1",
    )

    assert record.title == "Hello World"
    assert record.tags == ["daily-notes"]


def test_record_rejects_invalid_slug_and_markdown() -> None:
    with pytest.raises(ValidationError):
        Record(
            space="personal",
            slug="Hello World",
            title="Hello",
            body_markdown="# Hello",
            owner_id="user-1",
        )
    with pytest.raises(ValidationError):
        Record(
            space="personal",
            slug="hello",
            title="Hello",
            body_markdown="   ",
            owner_id="user-1",
        )


def test_record_and_personal_access_token_require_explicit_owners_and_actor() -> None:
    with pytest.raises(ValidationError, match="owner_id"):
        Record(space="personal", slug="note", title="Note", body_markdown="# Note")

    with pytest.raises(ValidationError, match="owner_id"):
        PersonalAccessToken(
            id="token-1",
            name="ChatGPT",
            token_hash="hash",
            scopes=frozenset({"records:read"}),
            allowed_spaces=frozenset({"personal"}),
        )

    with pytest.raises(ValidationError, match="actor_id"):
        PersonalAccessToken(
            id="token-1",
            name="API credential",
            token_hash="hash",
            scopes=frozenset({"records:read"}),
            allowed_spaces=frozenset({"personal"}),
            owner_id="owner",
        )


def test_record_list_defaults_are_not_shared() -> None:
    first = Record(
        space="personal",
        slug="first",
        title="First",
        body_markdown="# First",
        owner_id="user-1",
    )
    second = Record(
        space="personal",
        slug="second",
        title="Second",
        body_markdown="# Second",
        owner_id="user-1",
    )

    first.tags.append("one")
    first.revisions.append(
        RecordRevision(
            revision_id="rev-1",
            author_id="user-1",
            timestamp=datetime.now(UTC),
            body_markdown="# First updated",
        )
    )

    assert second.tags == []
    assert second.revisions == []


def test_space_tag_user_and_membership_models_validate_minimum_contract() -> None:
    space = Space(slug="personal", name="Personal", owner_id="user-1")
    tag = Tag(space="personal", slug="daily-notes", label="Daily Notes")
    user = User(id="user-1", display_name="Dev User")
    membership = Membership(user_id="user-1", space="personal", role="owner")

    assert space.slug == "personal"
    assert tag.label == "Daily Notes"
    assert user.display_name == "Dev User"
    assert membership.role == "owner"


def test_domain_models_reject_blank_identifiers_and_invalid_labels() -> None:
    with pytest.raises(ValidationError):
        Space(slug="personal", name="Personal", owner_id=" ")

    with pytest.raises(ValidationError):
        Tag(space="personal", slug="daily-notes", label=" ")

    with pytest.raises(ValidationError):
        User(id=" ", display_name="Dev User")


def test_record_optional_fields_default_to_empty_relationships() -> None:
    record = Record(
        space="personal",
        slug="standalone",
        title="Standalone",
        body_markdown="# Note",
        owner_id="user-1",
    )

    assert record.id is None
    assert record.parent_id is None
    assert record.path is None
    assert record.tags == []
    assert record.revisions == []
    assert record.visibility == "private"
    assert record.index_after is None


def test_membership_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        Membership(user_id="user-1", space="personal", role="admin")
