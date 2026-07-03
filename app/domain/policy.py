from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

RecordVisibility = Literal["private", "public"]

INDEX_DELAY = timedelta(days=7)
DEFAULT_ROBOTS_CONTENT = "noindex,nofollow,noarchive"


class CrawlerMetadata(BaseModel):
    index: bool
    follow: bool
    archive: bool

    @property
    def robots_content(self) -> str:
        index_value = "index" if self.index else "noindex"
        follow_value = "follow" if self.follow else "nofollow"
        archive_value = "archive" if self.archive else "noarchive"
        return ",".join([index_value, follow_value, archive_value])


def default_crawler_metadata() -> CrawlerMetadata:
    return CrawlerMetadata(index=False, follow=False, archive=False)


def public_index_after(now: datetime | None = None) -> datetime:
    base_time = now or datetime.now(UTC)
    return base_time + INDEX_DELAY


def next_index_after_for_create(
    visibility: RecordVisibility,
    index_after: datetime | None,
    now: datetime | None = None,
) -> datetime | None:
    if visibility == "public" and index_after is None:
        return public_index_after(now)
    return index_after


def next_index_after_for_update(
    *,
    current_visibility: RecordVisibility,
    next_visibility: RecordVisibility,
    index_after: datetime | None,
    index_after_was_provided: bool,
    now: datetime | None = None,
) -> datetime | None:
    if (
        current_visibility != "public"
        and next_visibility == "public"
        and not index_after_was_provided
    ):
        return public_index_after(now)
    return index_after


def crawler_metadata_for_record(
    *,
    visibility: RecordVisibility,
    index_after: datetime | None,
    now: datetime | None = None,
) -> CrawlerMetadata:
    if visibility == "private":
        return default_crawler_metadata()

    current_time = now or datetime.now(UTC)
    if index_after is not None and current_time < index_after:
        return CrawlerMetadata(index=False, follow=True, archive=False)

    return CrawlerMetadata(index=True, follow=True, archive=True)
