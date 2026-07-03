from datetime import UTC, datetime, timedelta

from app.domain.policy import (
    crawler_metadata_for_record,
    default_crawler_metadata,
    next_index_after_for_create,
    next_index_after_for_update,
)


def test_default_crawler_metadata_is_private_and_noindex() -> None:
    metadata = default_crawler_metadata()

    assert metadata.robots_content == "noindex,nofollow,noarchive"


def test_public_record_before_index_after_is_noindex_but_followable() -> None:
    now = datetime(2026, 7, 3, tzinfo=UTC)
    metadata = crawler_metadata_for_record(
        visibility="public",
        index_after=now + timedelta(days=1),
        now=now,
    )

    assert metadata.robots_content == "noindex,follow,noarchive"


def test_public_record_after_index_after_is_indexable() -> None:
    now = datetime(2026, 7, 10, tzinfo=UTC)
    metadata = crawler_metadata_for_record(
        visibility="public",
        index_after=now - timedelta(seconds=1),
        now=now,
    )

    assert metadata.robots_content == "index,follow,archive"


def test_public_create_without_override_defaults_to_seven_day_delay() -> None:
    now = datetime(2026, 7, 3, tzinfo=UTC)

    assert next_index_after_for_create("public", None, now) == now + timedelta(days=7)


def test_private_to_public_update_without_override_defaults_to_seven_day_delay() -> None:
    now = datetime(2026, 7, 3, tzinfo=UTC)

    assert next_index_after_for_update(
        current_visibility="private",
        next_visibility="public",
        index_after=None,
        index_after_was_provided=False,
        now=now,
    ) == now + timedelta(days=7)
