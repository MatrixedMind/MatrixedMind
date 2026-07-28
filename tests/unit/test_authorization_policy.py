import pytest

from app.domain.policy import PolicyRule, can_discover, can_edit, can_read, can_share


@pytest.mark.parametrize(
    "principal_type",
    ["user", "organization", "org_group", "external_group", "public"],
)
def test_each_principal_type_can_receive_explicit_access(principal_type: str) -> None:
    principals = {(principal_type, "principal")}
    rules = [
        PolicyRule(
            principal_type=principal_type,  # type: ignore[arg-type]
            principal_id="principal",
            action="read",
            effect="allow",
        )
    ]
    assert can_read(principals=principals, global_rules=rules)


def test_policy_is_private_by_default() -> None:
    assert not can_read(principals={("user", "owner")})
    assert not can_edit(principals={("user", "owner")})
    assert not can_share(principals={("user", "owner")})
    assert not can_discover(principals={("user", "owner")})


def test_more_specific_rule_wins_and_explicit_deny_wins() -> None:
    principals = {("user", "owner")}
    global_rules = [
        PolicyRule(principal_type="user", principal_id="owner", action="read", effect="deny")
    ]
    space_rules = [
        PolicyRule(principal_type="user", principal_id="owner", action="read", effect="allow")
    ]
    record_rules = [
        PolicyRule(principal_type="user", principal_id="owner", action="read", effect="deny"),
        PolicyRule(principal_type="user", principal_id="owner", action="read", effect="allow"),
    ]
    assert can_read(principals=principals, space_rules=space_rules)
    assert not can_read(
        principals=principals,
        global_rules=global_rules,
        space_rules=space_rules,
    )
    assert not can_read(
        principals=principals,
        global_rules=global_rules,
        space_rules=space_rules,
        record_rules=record_rules,
    )
