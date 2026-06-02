# Testing Strategy

## What verified means

A milestone is verified only when its listed commands and manual checks pass, or when failures are documented with exact blockers and the next fix path.

## Unit tests

Use fast tests for domain models, services, parsing, validation, and repository contracts. Unit tests should not require Docker or cloud credentials.

Expected checks:

```bash
uv run pytest tests/unit
```

## Integration tests

Use integration tests for local MongoDB behavior and adapter contract coverage. These tests may require Docker Compose or a test container, but they must not require GCP credentials for Mongo-only flows.

Expected checks:

```bash
docker compose up -d mongo
uv run pytest tests/integration
```

## API tests

Use FastAPI `TestClient` or `httpx` tests for route behavior. Cover success responses, validation errors, not-found responses, and repository dependency overrides.

## Web tests

Use server-rendered page tests first. Verify pages return the correct status code and render expected content. Full browser automation can wait until the UI becomes complex enough to justify it.

## Infrastructure checks

For Terraform changes:

```bash
terraform fmt -check
terraform validate
terraform plan
```

For container changes:

```bash
docker build -t matrixedmind:local .
```

For CI changes, open a pull request or run the workflow through the closest supported local equivalent, then document what was actually verified.

## Test data

Prefer small fixtures with explicit records, spaces, users, and revisions. Tests should avoid hidden dependency on execution order.

## Regression rule

Every bug fix should add a test that fails before the fix and passes after it unless the failure is purely documentation, configuration, or an external service incident.
