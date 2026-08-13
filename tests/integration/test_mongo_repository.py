from collections.abc import Iterator

import pytest
from pymongo import MongoClient

from app.adapters.mongo.repository import MongoRecordRepository
from app.domain.models import Record
from tests.contracts.record_repository_contract import assert_record_repository_contract

LOCAL_MONGO_URI = (
    "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind"
    "?authSource=admin&replicaSet=rs0&directConnection=true&retryWrites=false"
)


@pytest.fixture
def repo() -> Iterator[MongoRecordRepository]:
    client: MongoClient[dict[str, object]] = MongoClient(
        LOCAL_MONGO_URI,
        serverSelectionTimeoutMS=2000,
    )
    db = client.matrixed_mind_test
    db.records.drop()
    try:
        yield MongoRecordRepository(db)
    finally:
        db.records.drop()
        client.close()


def test_mongo_record_repository_satisfies_contract(repo: MongoRecordRepository) -> None:
    assert_record_repository_contract(repo)


def test_mongo_repository_rejects_duplicate_slugs(repo: MongoRecordRepository) -> None:
    repo.create(
        Record(
            space="personal",
            slug="daily-note",
            title="Daily Note",
            body_markdown="# Daily Note",
            owner_id="owner",
        )
    )

    with pytest.raises(ValueError, match="record already exists"):
        repo.create(
            Record(
                space="personal",
                slug="daily-note",
                title="Duplicate Daily Note",
                body_markdown="# Duplicate",
                owner_id="owner",
            )
        )

    same_slug_other_space = repo.create(
        Record(
            space="work",
            slug="daily-note",
            title="Work Daily Note",
            body_markdown="# Work Daily Note",
            owner_id="owner",
        )
    )

    assert same_slug_other_space.id is not None


def test_mongo_repository_update_creates_revision(repo: MongoRecordRepository) -> None:
    created = repo.create(
        Record(
            space="personal",
            slug="revision-test",
            title="Revision Test",
            body_markdown="# Original",
            owner_id="owner",
            updated_by="original-author",
        )
    )
    assert created.id is not None

    updated = repo.update(
        "owner",
        created.id,
        Record(
            space="personal",
            slug="revision-test",
            title="Revision Test",
            body_markdown="# Updated",
            owner_id="owner",
        ),
        actor_id="updated-by-owner",
    )
    fetched = repo.get_by_slug("owner", "personal", "revision-test")

    assert fetched == updated
    assert fetched is not None
    assert fetched.body_markdown == "# Updated"
    assert len(fetched.revisions) == 1
    assert fetched.revisions[0].body_markdown == "# Original"
    assert fetched.revisions[0].author_id == "original-author"


def test_mongo_repository_lists_by_space_and_parent(repo: MongoRecordRepository) -> None:
    root = repo.create(
        Record(
            space="personal",
            slug="root",
            title="Root",
            body_markdown="# Root",
            owner_id="owner",
        )
    )
    assert root.id is not None
    child = repo.create(
        Record(
            parent_id=root.id,
            space="personal",
            slug="child",
            title="Child",
            body_markdown="# Child",
            owner_id="owner",
        )
    )
    repo.create(
        Record(
            space="work",
            slug="root",
            title="Work Root",
            body_markdown="# Work Root",
            owner_id="owner",
        )
    )

    assert repo.list_children("owner", "personal", None) == [root]
    assert repo.list_children("owner", "personal", root.id) == [child]


def test_mongo_repository_update_missing_record_raises_key_error(
    repo: MongoRecordRepository,
) -> None:
    with pytest.raises(KeyError, match="record not found"):
        repo.update(
            "owner",
            "64b7f25f9f9a9f9a9f9a9f9a",
            Record(
                space="personal",
                slug="missing",
                title="Missing",
                body_markdown="# Missing",
                owner_id="owner",
            ),
            actor_id="owner",
        )
