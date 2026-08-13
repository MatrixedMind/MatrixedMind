from app.adapters.memory.repository import InMemoryTestPersonalAccessTokenRepository
from tests.contracts.api_credential_repository_contract import (
    assert_personal_access_token_repository_contract,
)


def test_personal_access_token_repository_contract() -> None:
    assert_personal_access_token_repository_contract(InMemoryTestPersonalAccessTokenRepository())
