from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from pymongo import MongoClient

from app.adapters.mongo.auth import MongoOwnerAuthRepository
from app.auth.service import (
    hash_opaque_secret,
    hash_password,
    issue_operator_credential,
    issue_session,
    refresh_session,
)
from app.domain.models import OwnerCredential
from app.settings import Settings

LOCAL_MONGO_URI = (
    "mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind"
    "?authSource=admin&replicaSet=rs0&directConnection=true&retryWrites=false"
)
NOW = datetime(2026, 8, 13, tzinfo=UTC)
CONFIGURED = Settings(operator_credential_ttl_seconds=60)


@pytest.fixture
def repo() -> Iterator[MongoOwnerAuthRepository]:
    client: MongoClient[dict[str, object]] = MongoClient(
        LOCAL_MONGO_URI,
        serverSelectionTimeoutMS=2000,
    )
    db = client.matrixed_mind_auth_test
    for name in ("owner_credentials", "browser_sessions", "owner_one_time_credentials"):
        db[name].drop()
    try:
        yield MongoOwnerAuthRepository(db)
    finally:
        for name in ("owner_credentials", "browser_sessions", "owner_one_time_credentials"):
            db[name].drop()
        client.close()


def owner(password: str = "correct horse battery staple") -> OwnerCredential:
    return OwnerCredential(
        owner_id="owner",
        display_name="Owner",
        password_hash=hash_password(password),
        created_at=NOW,
        password_changed_at=NOW,
    )


def bootstrap(repo: MongoOwnerAuthRepository) -> OwnerCredential:
    credential = owner()
    raw = issue_operator_credential(repo, "bootstrap", CONFIGURED, now=NOW)
    assert repo.bootstrap_owner(credential, hash_opaque_secret(raw), NOW)
    assert not repo.bootstrap_owner(credential, hash_opaque_secret(raw), NOW)
    assert repo.get_owner() == credential
    return credential


def test_mongo_bootstrap_session_persistence_and_monotonic_revocation(
    repo: MongoOwnerAuthRepository,
) -> None:
    bootstrap(repo)
    issued = issue_session("owner", CONFIGURED, now=NOW)
    stale = issued.session.model_copy(deep=True)
    assert repo.save_session(issued.session) == issued.session
    repo.revoke_session(issued.session.id, NOW + timedelta(seconds=1))

    persisted = repo.save_session(
        stale.model_copy(update={"last_seen_at": NOW + timedelta(seconds=2)})
    )

    assert persisted.revoked_at == NOW + timedelta(seconds=1)


def test_mongo_stale_refresh_cannot_revert_session_rotation(
    repo: MongoOwnerAuthRepository,
) -> None:
    bootstrap(repo)
    configured = Settings(session_rotation_seconds=10)
    issued = issue_session("owner", configured, now=NOW)
    repo.save_session(issued.session)
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
        repo.save_session(
            issued.session.model_copy(update={"last_seen_at": NOW + timedelta(seconds=1)}),
            previous_token_hash=issued.session.token_hash,
        )

    assert repo.get_session_by_hash(rotated.session.token_hash) == rotated.session


def test_mongo_revoked_session_cannot_refresh_with_same_token_hash(
    repo: MongoOwnerAuthRepository,
) -> None:
    bootstrap(repo)
    issued = issue_session("owner", CONFIGURED, now=NOW)
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


def test_mongo_password_change_keeps_only_current_session(
    repo: MongoOwnerAuthRepository,
) -> None:
    credential = bootstrap(repo)
    current = issue_session("owner", CONFIGURED, now=NOW)
    other = issue_session("owner", CONFIGURED, now=NOW)
    repo.save_session(current.session)
    repo.save_session(other.session)
    changed_at = NOW + timedelta(seconds=10)

    assert repo.change_password(
        credential.model_copy(
            update={
                "password_hash": hash_password("another secure owner password"),
                "password_changed_at": changed_at,
            }
        ),
        current.session.id,
        credential.password_hash,
        changed_at,
    )

    assert repo.get_session_by_hash(current.session.token_hash).revoked_at is None  # type: ignore[union-attr]
    assert repo.get_session_by_hash(other.session.token_hash).revoked_at == changed_at  # type: ignore[union-attr]


def test_mongo_password_change_requires_expected_hash_and_active_session(
    repo: MongoOwnerAuthRepository,
) -> None:
    credential = bootstrap(repo)
    active = issue_session("owner", CONFIGURED, now=NOW)
    revoked = issue_session("owner", CONFIGURED, now=NOW)
    repo.save_session(active.session)
    repo.save_session(revoked.session)
    repo.revoke_session(revoked.session.id, NOW + timedelta(seconds=1))
    replacement = credential.model_copy(
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
        credential.password_hash,
        NOW + timedelta(seconds=2),
    )
    assert repo.get_owner() == credential


def test_mongo_recovery_atomically_consumes_and_revokes_all_sessions(
    repo: MongoOwnerAuthRepository,
) -> None:
    credential = bootstrap(repo)
    issued = issue_session("owner", CONFIGURED, now=NOW)
    repo.save_session(issued.session)
    raw = issue_operator_credential(repo, "recovery", CONFIGURED, now=NOW)
    changed_at = NOW + timedelta(seconds=20)
    recovered = credential.model_copy(
        update={
            "password_hash": hash_password("recovered secure owner password"),
            "password_changed_at": changed_at,
        }
    )

    assert repo.recover_owner(recovered, hash_opaque_secret(raw), changed_at)
    assert not repo.recover_owner(recovered, hash_opaque_secret(raw), changed_at)
    assert repo.get_owner() == recovered
    assert repo.get_session_by_hash(issued.session.token_hash).revoked_at == changed_at  # type: ignore[union-attr]
    stale_change = credential.model_copy(
        update={"password_hash": hash_password("stale requested password")}
    )
    assert not repo.change_password(
        stale_change,
        issued.session.id,
        credential.password_hash,
        changed_at + timedelta(seconds=1),
    )
    assert repo.get_owner() == recovered
