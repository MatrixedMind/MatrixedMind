from unittest.mock import Mock

from app import dependencies


def test_get_record_repository_caches_repository_instance() -> None:
    dependencies._get_cached_record_repository.cache_clear()
    original_build = dependencies._build_record_repository

    try:
        repo = Mock(name="repo")
        build_repository = Mock(return_value=repo)
        dependencies._build_record_repository = build_repository

        first = dependencies.get_record_repository()
        second = dependencies.get_record_repository()

        assert first is repo
        assert second is repo
        assert build_repository.call_count == 1
    finally:
        dependencies._build_record_repository = original_build
        dependencies._get_cached_record_repository.cache_clear()
