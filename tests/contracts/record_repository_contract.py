import pytest

from app.domain.models import Record
from app.domain.ports import RecordRepository


def assert_record_repository_contract(repo: RecordRepository) -> None:
    """Verify behavior every RecordRepository adapter must provide."""
    root = repo.create(
        Record(
            space="personal",
            slug="root",
            title="Root",
            body_markdown="# Root",
            path="/root",
            owner_id="owner",
        )
    )
    child = repo.create(
        Record(
            parent_id=root.id,
            space="personal",
            slug="child",
            title="Child",
            body_markdown="# Child",
            path="/root/child",
            owner_id="owner",
            created_by="original-creator",
            updated_by="original-author",
        )
    )
    repo.create(
        Record(
            space="work",
            slug="root",
            title="Work Root",
            body_markdown="# Work Root",
            path="/root",
            owner_id="owner",
        )
    )

    assert root.id is not None
    assert child.id is not None
    assert repo.get_by_slug("owner", "personal", "root") == root
    assert repo.get_by_slug("owner", "personal", "missing") is None
    assert repo.list_children("owner", "personal", None) == [root]
    assert repo.list_children("owner", "personal", root.id) == [child]
    assert repo.list_children("owner", "personal", "missing-parent") == []
    assert repo.list_children("owner", "missing-space", None) == []

    with pytest.raises(ValueError, match="record already exists"):
        repo.create(
            Record(
                space="personal",
                slug="root",
                title="Duplicate Root",
                body_markdown="# Duplicate Root",
                owner_id="owner",
            )
        )

    with pytest.raises(ValueError, match="record already exists"):
        repo.update(
            "owner",
            child.id,
            child.model_copy(update={"parent_id": None, "slug": "root"}),
            actor_id="owner",
        )
    assert repo.get_by_slug("owner", "personal", "child") == child

    with pytest.raises(ValueError, match="owner_id cannot change"):
        repo.update(
            "owner",
            child.id,
            child.model_copy(update={"owner_id": "other-owner"}),
            actor_id="owner",
        )
    assert repo.get_by_slug("owner", "personal", "child") == child

    updated = repo.update(
        "owner",
        child.id,
        Record(
            id=child.id,
            parent_id=root.id,
            space="personal",
            slug="child",
            title="Updated Child",
            body_markdown="# Updated Child",
            path="/root/child",
            owner_id="owner",
        ),
        actor_id="updated-by-owner",
    )

    fetched = repo.get_by_slug("owner", "personal", "child")

    assert fetched is not None
    assert updated.id == child.id
    assert fetched == updated
    assert fetched.title == "Updated Child"
    assert fetched.created_by == "original-creator"
    assert fetched.revisions[-1].author_id == "original-author"

    with pytest.raises(KeyError):
        repo.update(
            "owner",
            "missing-record",
            Record(
                space="personal",
                slug="missing",
                title="Missing",
                body_markdown="# Missing",
                owner_id="owner",
            ),
            actor_id="owner",
        )

    same_slug_other_owner = repo.create(
        Record(
            space="personal",
            slug="root",
            title="Other Owner Root",
            body_markdown="# Other Root",
            owner_id="other-owner",
        )
    )
    assert repo.get_by_slug("other-owner", "personal", "root") == same_slug_other_owner
    assert repo.get_by_slug("owner", "personal", "root") == root

    with pytest.raises(KeyError):
        repo.update(
            "other-owner",
            root.id,
            root.model_copy(update={"title": "Cross-owner update"}),
            actor_id="other-owner",
        )
