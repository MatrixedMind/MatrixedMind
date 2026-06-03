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
        )
    )
    repo.create(
        Record(
            space="work",
            slug="root",
            title="Work Root",
            body_markdown="# Work Root",
            path="/root",
        )
    )

    assert root.id is not None
    assert child.id is not None
    assert repo.get_by_slug("personal", "root") == root
    assert repo.get_by_slug("personal", "missing") is None
    assert repo.list_children("personal", None) == [root]
    assert repo.list_children("personal", root.id) == [child]
    assert repo.list_children("personal", "missing-parent") == []
    assert repo.list_children("missing-space", None) == []

    updated = repo.update(
        child.id,
        Record(
            id=child.id,
            parent_id=root.id,
            space="personal",
            slug="child",
            title="Updated Child",
            body_markdown="# Updated Child",
            path="/root/child",
        ),
    )

    fetched = repo.get_by_slug("personal", "child")

    assert fetched is not None
    assert updated.id == child.id
    assert fetched == updated
    assert fetched.title == "Updated Child"

    with pytest.raises(KeyError):
        repo.update(
            "missing-record",
            Record(
                space="personal",
                slug="missing",
                title="Missing",
                body_markdown="# Missing",
            ),
        )
