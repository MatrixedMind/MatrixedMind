from pathlib import Path


def test_production_container_does_not_sync_dependencies_at_startup() -> None:
    dockerfile = Path(__file__).parents[2] / "Dockerfile"

    assert (
        'CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", '
        '"--host", "0.0.0.0", "--port", "8080"]'
    ) in dockerfile.read_text()
