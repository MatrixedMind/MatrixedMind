import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]


def _ignored_top_level_paths(ignore_file: Path) -> set[str]:
    return {
        line.removesuffix("/")
        for raw_line in ignore_file.read_text().splitlines()
        if (line := raw_line.strip()) and not line.startswith(("#", "!"))
    }


def test_production_container_does_not_sync_dependencies_at_startup() -> None:
    dockerfile = REPOSITORY_ROOT / "Dockerfile"

    command_line = next(
        line for line in dockerfile.read_text().splitlines() if line.startswith("CMD ")
    )
    command = json.loads(command_line.removeprefix("CMD "))

    assert command == [
        "uv",
        "run",
        "--no-sync",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8080",
    ]


def test_firestore_test_container_has_its_required_build_context() -> None:
    production_ignores = _ignored_top_level_paths(REPOSITORY_ROOT / ".dockerignore")
    firestore_ignores = _ignored_top_level_paths(
        REPOSITORY_ROOT / "Dockerfile.firestore-test.dockerignore"
    )
    required_paths = {"Dockerfile.firestore-test", "scripts", "tests"}

    assert required_paths <= production_ignores
    assert required_paths.isdisjoint(firestore_ignores)
