from app.adapters.memory.repository import InMemoryRecordRepository
from tests.contracts.record_repository_contract import assert_record_repository_contract


def test_record_repository_contract_create_get_list_and_update() -> None:
    assert_record_repository_contract(InMemoryRecordRepository())
