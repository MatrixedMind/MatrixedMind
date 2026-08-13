from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.memory.auth import InMemoryOwnerAuthRepository
from app.auth.service import (
    authentication_attempt_limiter,
    hash_opaque_secret,
    hash_password,
    issue_operator_credential,
    issue_session,
    refresh_session,
    valid_csrf,
    validate_password,
    verify_password,
)
from app.domain.models import OwnerCredential
from app.settings import Settings

NOW = datetime(2026, 8, 13, tzinfo=UTC)
PASSWORD = "correct horse battery staple"


@pytest.mark.parametrize("password", ["", " " * 12, "short", "valid password\x00"])
def test_password_validation_rejects_invalid_values(password: str) -> None:
    with pytest.raises(ValueError):
        validate_password(password)


def test_password_validation_accepts_boundaries_and_rejects_oversized() -> None:
    assert validate_password("x" * 12) == "x" * 12
    assert validate_password("x" * 1024) == "x" * 1024
    with pytest.raises(ValueError, match="at most"):
        validate_password("x" * 1025)


def test_argon2id_hash_is_verifiable_and_contains_no_password() -> None:
    password_hash = hash_password(PASSWORD)
    assert password_hash.startswith("$argon2id$")
    assert PASSWORD not in password_hash
    assert verify_password(password_hash, PASSWORD)
    assert not verify_password(password_hash, "wrong password")
    assert not verify_password(password_hash, "x" * 1025)


def test_bootstrap_is_one_time_atomic_and_expiring() -> None:
    configured = Settings(operator_credential_ttl_seconds=60)
    repo = InMemoryOwnerAuthRepository()
    raw_token = issue_operator_credential(repo, "bootstrap", configured, now=NOW)
    owner = OwnerCredential(
        owner_id="owner", display_name="Owner", password_hash=hash_password(PASSWORD)
    )

    assert repo.bootstrap_owner(owner, hash_opaque_secret(raw_token), NOW + timedelta(seconds=59))
    assert not repo.bootstrap_owner(
        owner, hash_opaque_secret(raw_token), NOW + timedelta(seconds=59)
    )

    expired_repo = InMemoryOwnerAuthRepository()
    expired = issue_operator_credential(expired_repo, "bootstrap", configured, now=NOW)
    assert not expired_repo.bootstrap_owner(
        owner, hash_opaque_secret(expired), NOW + timedelta(seconds=60)
    )
    assert expired_repo.get_owner() is None


def test_recovery_atomically_changes_password_and_revokes_sessions() -> None:
    configured = Settings(operator_credential_ttl_seconds=60)
    repo = InMemoryOwnerAuthRepository()
    bootstrap = issue_operator_credential(repo, "bootstrap", configured, now=NOW)
    owner = OwnerCredential(
        owner_id="owner", display_name="Owner", password_hash=hash_password(PASSWORD)
    )
    assert repo.bootstrap_owner(owner, hash_opaque_secret(bootstrap), NOW)
    issued = issue_session("owner", configured, now=NOW)
    repo.save_session(issued.session)
    recovery = issue_operator_credential(repo, "recovery", configured, now=NOW)
    replacement = owner.model_copy(
        update={
            "password_hash": hash_password("another secure owner password"),
            "password_changed_at": NOW + timedelta(seconds=30),
        }
    )

    assert repo.recover_owner(
        replacement, hash_opaque_secret(recovery), NOW + timedelta(seconds=30)
    )
    assert repo.get_session_by_hash(issued.session.token_hash).revoked_at is not None  # type: ignore[union-attr]
    assert not repo.recover_owner(
        replacement, hash_opaque_secret(recovery), NOW + timedelta(seconds=31)
    )


def test_invalid_recovery_does_not_change_owner_or_sessions() -> None:
    configured = Settings()
    repo = InMemoryOwnerAuthRepository()
    bootstrap = issue_operator_credential(repo, "bootstrap", configured, now=NOW)
    owner = OwnerCredential(
        owner_id="owner", display_name="Owner", password_hash=hash_password(PASSWORD)
    )
    assert repo.bootstrap_owner(owner, hash_opaque_secret(bootstrap), NOW)
    issued = issue_session("owner", configured, now=NOW)
    repo.save_session(issued.session)
    changed = owner.model_copy(update={"password_hash": hash_password("replacement password!")})

    assert not repo.recover_owner(changed, hash_opaque_secret("invalid"), NOW)
    assert repo.get_owner().password_hash == owner.password_hash  # type: ignore[union-attr]
    assert repo.get_session_by_hash(issued.session.token_hash).revoked_at is None  # type: ignore[union-attr]


def test_recovery_wins_over_stale_password_change() -> None:
    configured = Settings()
    repo = InMemoryOwnerAuthRepository()
    bootstrap = issue_operator_credential(repo, "bootstrap", configured, now=NOW)
    owner = OwnerCredential(
        owner_id="owner", display_name="Owner", password_hash=hash_password(PASSWORD)
    )
    assert repo.bootstrap_owner(owner, hash_opaque_secret(bootstrap), NOW)
    issued = issue_session("owner", configured, now=NOW)
    repo.save_session(issued.session)
    recovery = issue_operator_credential(repo, "recovery", configured, now=NOW)
    recovered = owner.model_copy(
        update={
            "password_hash": hash_password("recovered secure owner password"),
            "password_changed_at": NOW + timedelta(seconds=1),
        }
    )
    assert repo.recover_owner(recovered, hash_opaque_secret(recovery), NOW + timedelta(seconds=1))

    assert not repo.change_password(
        owner.model_copy(update={"password_hash": hash_password("stale requested password")}),
        issued.session.id,
        owner.password_hash,
        NOW + timedelta(seconds=2),
    )
    assert repo.get_owner() == recovered


def test_password_change_requires_expected_hash_and_active_session() -> None:
    configured = Settings()
    repo = InMemoryOwnerAuthRepository()
    bootstrap = issue_operator_credential(repo, "bootstrap", configured, now=NOW)
    owner = OwnerCredential(
        owner_id="owner", display_name="Owner", password_hash=hash_password(PASSWORD)
    )
    assert repo.bootstrap_owner(owner, hash_opaque_secret(bootstrap), NOW)
    active = issue_session("owner", configured, now=NOW)
    revoked = issue_session("owner", configured, now=NOW)
    repo.save_session(active.session)
    repo.save_session(revoked.session)
    repo.revoke_session(revoked.session.id, NOW + timedelta(seconds=1))
    replacement = owner.model_copy(
        update={"password_hash": hash_password("replacement secure password")}
    )

    assert not repo.change_password(
        replacement,
        active.session.id,
        "wrong-expected-hash",
        NOW + timedelta(seconds=2),
    )
    assert not repo.change_password(
        replacement,
        revoked.session.id,
        owner.password_hash,
        NOW + timedelta(seconds=2),
    )
    assert repo.get_owner() == owner


def test_session_inactivity_absolute_expiry_rotation_and_csrf() -> None:
    configured = Settings(
        session_inactivity_seconds=100,
        session_absolute_seconds=500,
        session_rotation_seconds=50,
    )
    issued = issue_session("owner", configured, now=NOW)
    assert valid_csrf(issued.session, issued.raw_csrf_token, issued.raw_csrf_token)
    assert not valid_csrf(issued.session, issued.raw_csrf_token, "wrong")

    active = refresh_session(
        issued.session,
        issued.raw_token,
        issued.raw_csrf_token,
        configured,
        now=NOW + timedelta(seconds=49),
    )
    assert active is not None and active.raw_token == issued.raw_token
    rotated = refresh_session(
        issued.session,
        issued.raw_token,
        issued.raw_csrf_token,
        configured,
        now=NOW + timedelta(seconds=50),
    )
    assert rotated is not None and rotated.raw_token != issued.raw_token
    assert (
        refresh_session(
            issued.session,
            issued.raw_token,
            issued.raw_csrf_token,
            configured,
            now=NOW + timedelta(seconds=100),
        )
        is None
    )
    assert (
        refresh_session(
            issued.session,
            issued.raw_token,
            issued.raw_csrf_token,
            configured,
            now=NOW + timedelta(seconds=500),
        )
        is None
    )


def test_attempt_limiter_is_bounded_and_resettable() -> None:
    configured = Settings(auth_attempt_limit=2)
    authentication_attempt_limiter.clear()
    assert authentication_attempt_limiter.check("login:client", configured)
    assert authentication_attempt_limiter.check("login:client", configured)
    assert not authentication_attempt_limiter.check("login:client", configured)
    authentication_attempt_limiter.reset("login:client")
    assert authentication_attempt_limiter.check("login:client", configured)


def test_stale_session_save_cannot_clear_revocation() -> None:
    configured = Settings()
    repo = InMemoryOwnerAuthRepository()
    issued = issue_session("owner", configured, now=NOW)
    stale = issued.session.model_copy(deep=True)
    repo.save_session(issued.session)
    repo.revoke_session(issued.session.id, NOW + timedelta(seconds=1))

    saved = repo.save_session(stale.model_copy(update={"last_seen_at": NOW + timedelta(seconds=2)}))

    assert saved.revoked_at == NOW + timedelta(seconds=1)


def test_stale_session_refresh_cannot_overwrite_rotated_credential() -> None:
    configured = Settings(session_rotation_seconds=10)
    repo = InMemoryOwnerAuthRepository()
    issued = issue_session("owner", configured, now=NOW)
    repo.save_session(issued.session)
    stale = issued.session.model_copy(update={"last_seen_at": NOW + timedelta(seconds=1)})
    rotated = refresh_session(
        issued.session,
        issued.raw_token,
        issued.raw_csrf_token,
        configured,
        now=NOW + timedelta(seconds=10),
    )
    assert rotated is not None
    repo.save_session(rotated.session, previous_token_hash=issued.session.token_hash)

    with pytest.raises(RuntimeError, match="changed concurrently"):
        repo.save_session(stale, previous_token_hash=issued.session.token_hash)

    assert repo.get_session_by_hash(rotated.session.token_hash) == rotated.session


def test_revoked_session_cannot_be_refreshed_with_same_token_hash() -> None:
    configured = Settings()
    repo = InMemoryOwnerAuthRepository()
    issued = issue_session("owner", configured, now=NOW)
    repo.save_session(issued.session)
    repo.revoke_session(issued.session.id, NOW + timedelta(seconds=1))

    with pytest.raises(RuntimeError, match="changed concurrently"):
        repo.save_session(
            issued.session.model_copy(update={"last_seen_at": NOW + timedelta(seconds=2)}),
            previous_token_hash=issued.session.token_hash,
        )

    persisted = repo.get_session_by_hash(issued.session.token_hash)
    assert persisted is not None
    assert persisted.revoked_at == NOW + timedelta(seconds=1)
    assert persisted.last_seen_at == NOW
