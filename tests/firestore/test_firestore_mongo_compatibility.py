from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
from pymongo import MongoClient

from app.adapters.mongo.connection import MongoConnection
from app.adapters.mongo.repository import MongoRecordRepository
from app.domain.models import Record
from app.settings import settings
from tests.contracts.record_repository_contract import assert_record_repository_contract


def _record(slug: str, *, created_at: datetime | None = None) -> Record:
    return Record(
        space="firestore-spike",
        slug=slug,
        title=slug.replace("-", " ").title(),
        body_markdown=f"# {slug}",
        owner_id="firestore-spike-owner",
        created_at=created_at or datetime.now(UTC),
    )


def test_firestore_record_repository_satisfies_contract(
    firestore_repo: MongoRecordRepository,
) -> None:
    assert_record_repository_contract(firestore_repo)


def test_firestore_uses_object_ids(
    firestore_repo: MongoRecordRepository,
) -> None:
    created = firestore_repo.create(_record("object-id"))

    assert created.id is not None
    assert ObjectId.is_valid(created.id)
    stored = firestore_repo.collection.find_one({"space": "firestore-spike", "slug": "object-id"})
    assert stored is not None
    assert isinstance(stored["_id"], ObjectId)


def test_firestore_unique_compound_index_maps_duplicate_key_errors(
    firestore_repo: MongoRecordRepository,
) -> None:
    firestore_repo.create(_record("duplicate"))

    with pytest.raises(ValueError, match="record already exists"):
        firestore_repo.create(_record("duplicate"))

    other_space = _record("duplicate")
    other_space.space = "firestore-spike-other"
    assert firestore_repo.create(other_space).id is not None


def test_firestore_update_one_set_behavior(
    firestore_repo: MongoRecordRepository,
) -> None:
    created = firestore_repo.create(_record("update-set"))
    assert created.id is not None

    replacement = _record("update-set")
    replacement.title = "Updated through set"
    updated = firestore_repo.update(
        "firestore-spike-owner", created.id, replacement, actor_id="firestore-spike-actor"
    )

    assert updated.title == "Updated through set"
    assert updated.updated_by == "firestore-spike-actor"
    assert len(updated.revisions) == 1
    assert updated.revisions[0].body_markdown == "# update-set"


def test_firestore_sorting_is_deterministic(
    firestore_repo: MongoRecordRepository,
) -> None:
    now = datetime.now(UTC)
    second = firestore_repo.create(_record("second", created_at=now + timedelta(seconds=1)))
    first = firestore_repo.create(_record("first", created_at=now))

    assert firestore_repo.list_children("firestore-spike-owner", "firestore-spike", None) == [
        first,
        second,
    ]


def test_firestore_readiness_ping(
    firestore_client: MongoClient[dict[str, object]],
    firestore_mongo_uri: str,
) -> None:
    assert firestore_client.admin.command("ping")["ok"] == 1

    original_uri = settings.mongo_uri
    MongoConnection.disconnect()
    settings.mongo_uri = firestore_mongo_uri
    try:
        assert MongoConnection.ping() is True
    finally:
        MongoConnection.disconnect()
        settings.mongo_uri = original_uri
