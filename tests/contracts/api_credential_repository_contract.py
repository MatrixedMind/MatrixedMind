import pytest

from app.domain.models import PersonalAccessToken
from app.domain.ports import PersonalAccessTokenRepository


def _token(token_id: str, token_hash: str) -> PersonalAccessToken:
    return PersonalAccessToken(
        id=token_id,
        name=f"Credential {token_id}",
        token_hash=token_hash,
        scopes=frozenset({"records:read"}),
        allowed_spaces=frozenset({"personal"}),
        owner_id="owner",
        actor_id="pat:owner",
    )


def assert_personal_access_token_repository_contract(
    repo: PersonalAccessTokenRepository,
) -> None:
    """Verify storage semantics for hashed personal access tokens."""
    first = repo.save(_token("credential-1", "hash-one"))
    fetched_first = repo.get_by_hash("hash-one")
    assert fetched_first is not None
    assert fetched_first.id == first.id
    assert fetched_first.token_hash == first.token_hash

    rotated = repo.save(_token("credential-1", "hash-two"))
    assert repo.get_by_hash("hash-one") is None
    fetched_rotated = repo.get_by_hash("hash-two")
    assert fetched_rotated is not None
    assert fetched_rotated.id == rotated.id
    assert fetched_rotated.token_hash == rotated.token_hash

    with pytest.raises(ValueError, match="token hash already exists"):
        repo.save(_token("credential-2", "hash-two"))

    repo.revoke(rotated.id)
    revoked = repo.get_by_hash("hash-two")
    assert revoked is not None and revoked.is_revoked
    revoked_at = revoked.revoked_at
    assert revoked_at is not None

    rotated_after_revoke = repo.save(_token(rotated.id, "hash-three"))
    assert rotated_after_revoke.revoked_at == revoked_at
    assert repo.get_by_hash("hash-two") is None
    fetched_after_revoke = repo.get_by_hash("hash-three")
    assert fetched_after_revoke is not None
    assert fetched_after_revoke.revoked_at == revoked_at

    repo.revoke(rotated.id)
    still_revoked = repo.get_by_hash("hash-three")
    assert still_revoked is not None
    assert still_revoked.revoked_at == revoked_at

    with pytest.raises(KeyError, match="token not found"):
        repo.revoke("missing-credential")
