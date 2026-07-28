from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

RecordVisibility = Literal["private", "public"]
PrincipalType = Literal["user", "organization", "org_group", "external_group", "public"]
PolicyAction = Literal["read", "edit", "share", "discover"]

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


class Principal(BaseModel):
    type: PrincipalType
    id: str


class PolicyRule(BaseModel):
    principal_type: PrincipalType
    principal_id: str
    action: PolicyAction
    effect: Literal["allow", "deny"]


def policy_allows(
    *,
    principals: set[tuple[PrincipalType, str]],
    action: PolicyAction,
    global_rules: list[PolicyRule] | None = None,
    space_rules: list[PolicyRule] | None = None,
    record_rules: list[PolicyRule] | None = None,
) -> bool:
    """Evaluate explicit policy with deny-overrides and record/space/global precedence."""
    applicable_by_scope = [
        [
            rule
            for rule in rules
            if rule.action == action and (rule.principal_type, rule.principal_id) in principals
        ]
        for rules in (record_rules or [], space_rules or [], global_rules or [])
    ]
    if any(rule.effect == "deny" for rules in applicable_by_scope for rule in rules):
        return False
    for applicable in applicable_by_scope:
        if any(rule.effect == "allow" for rule in applicable):
            return True
    return False


def can_read(**kwargs: object) -> bool:
    return policy_allows(action="read", **kwargs)  # type: ignore[arg-type]


def can_edit(**kwargs: object) -> bool:
    return policy_allows(action="edit", **kwargs)  # type: ignore[arg-type]


def can_share(**kwargs: object) -> bool:
    return policy_allows(action="share", **kwargs)  # type: ignore[arg-type]


def can_discover(**kwargs: object) -> bool:
    return policy_allows(action="discover", **kwargs)  # type: ignore[arg-type]


def owner_can_discover_record(*, owner_id: str, visibility: RecordVisibility, user_id: str) -> bool:
    return user_id == owner_id or visibility == "public"


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
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    if index_after is not None:
        if index_after.tzinfo is None:
            index_after = index_after.replace(tzinfo=UTC)
        if current_time < index_after:
            return CrawlerMetadata(index=False, follow=True, archive=False)

    return CrawlerMetadata(index=True, follow=True, archive=True)
