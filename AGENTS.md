# Agent Guidelines

This document provides project-specific instructions for developers and AI agents working on the MatrixedMind project.

## 1. Build and Configuration Instructions

The project uses `uv` for dependency management and Python 3.12+.

### Local Setup
1. **Install uv**: If not already installed, follow the [uv installation guide](https://github.com/astral-sh/uv).
2. **Sync dependencies**:
   ```bash
   uv sync --locked
   ```
3. **Environment Variables**: Use `.env.example` as the template for local configuration.
4. **Pre-commit Hooks**: Must be used for local and CI validation.
   ```bash
   pre-commit install
   ```

### Docker Development
The repository includes a `Dockerfile` and `compose.yaml` for containerized development.
- **Default Stack**: `api` (FastAPI) and `mongo`.
- **Run with Compose**:
  ```bash
  docker compose up
  ```
- **Note**: Ensure the app can boot locally without GCP for core features. Integration tests should run without cloud credentials for Mongo-only flows.

## 2. Testing Information

### Configuring and Running Tests
- **Tool**: `pytest` is used for testing.
- **Run all tests**:
  ```bash
  uv run pytest
  ```
- **Run specific tests**:
  ```bash
  uv run pytest tests/unit/test_health.py
  ```

### Guidelines for Adding Tests
1. **Location**: Place unit tests in `tests/unit/` and integration tests in `tests/integration/`.
2. **Naming**: Test files should be prefixed with `test_`.
3. **Style**: Use standard `pytest` assertions.
4. **CI/CD**: PRs must pass all tests before merging.

### Demonstration Test
To verify your testing environment is set up correctly, you can create a simple test file `tests/demo_test.py`:
```python
import pytest

def test_simple_demo():
    assert 1 + 1 == 2
```
Then run it:
```bash
uv run pytest tests/demo_test.py
```

## 3. Additional Development Information

### Code Style and Quality
- **Linter/Formatter**: `ruff` is used for both linting and formatting.
  - Check: `uv run ruff check .`
  - Format: `uv run ruff format .`
- **Type Checking**: `mypy` is required for static type checking.
  - Run: `uv run mypy app tests`
- **Pre-commit**: Agents must not disable hooks. If a hook is noisy, update its configuration.

### GCP and Terraform Policy
- **Terraform Layout**: Roots are in `infra/terraform/envs/{dev,prod}`. Modules are in `infra/terraform/modules/*`.
- **State**: Backend is GCS with versioning enabled.
- **Deployment**: Targets Cloud Run via GitHub Actions using Workload Identity Federation. Avoid service-account keys.

### Secrets Handling
- **Never commit**: `.env`, `.envrc`, service-account JSON, or ADC credentials.
- **Secret Manager**: Use GCP Secret Manager for cloud secrets. Do not reference `latest` version in production.

### PyCharm Integration
- **Primary Interpreter**: Use the local `uv` interpreter.
- **Secondary**: Use Docker Compose interpreter for parity debugging.
- **Inspections**: Keep Git commit hooks enabled and use the Problems window for triage.

## 4. Troubleshooting Playbook

- **MongoDB on Apple Silicon**: If it behaves strangely in Docker, use the Apple Virtualization framework instead of Docker VMM.
- **Firestore Emulator**: Requires Java (prefer Java 21) and `firebase-tools`.
- **GCP Auth**: If code works in terminal but not in app, verify Application Default Credentials (ADC) with `gcloud auth application-default login`.

## 5. Final Operating Rule
Agents must leave the repository in a valid state: either passing all validations with a clear summary or failing with an exact list of blockers and the next best fix path. Silent partial work is unacceptable.
