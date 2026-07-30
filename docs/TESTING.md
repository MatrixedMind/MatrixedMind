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

Use integration tests for local MongoDB behavior, route behavior that crosses app boundaries, and adapter contract coverage. These tests may require Docker Compose or a test container for MongoDB-specific flows, but they must not require GCP credentials for Mongo-only flows.

Expected checks:

```bash
docker compose up -d mongo
uv run pytest tests/integration
```

MongoDB-backed tests use the local Compose service and the settings from `.env` or the safe defaults in `app/settings.py`; no seed data is required. If `tests/integration` cannot connect, first check that `docker compose ps` shows the `mongo` service as running, then verify that any local `MONGODB_URI` override points at the Compose MongoDB instance.

Current integration coverage includes a MongoDB ping test, MongoDB repository contract coverage, MongoDB duplicate/missing-record/revision behavior, and FastAPI route tests using in-memory adapters. Route tests cover owner protection, record CRUD, server-rendered flows, crawler metadata, scoped LLM create/update/read/list behavior, private defaults, revision and audit attribution, token revocation, forbidden capabilities, body limits, and rate limits. Unit tests cover the LLM-only OpenAPI allowlist and bearer security contract, authorization principal precedence, required ownership, and bounded streaming that stops consuming a request after it crosses the configured body limit.

Rendering tests cover approved external HTTPS images, exact and wildcard source allowlists, unsafe
schemes and authorities, raw-HTML policy parity, stripped event/style attributes, and preservation
of the existing safe-link behavior. Settings tests also verify that the hosted source offer can use
only a public HTTPS repository URL and either a local marker or a full lowercase Git commit SHA.

## Firestore MongoDB compatibility tests

Tests under `tests/firestore/` are opt-in and skip when `FIRESTORE_MONGO_URI` is absent. They run the
repository contract and explicit compatibility checks against a dedicated Firestore Enterprise
database. The canonical execution path is the Terraform-managed Cloud Run Job, which authenticates
with its service account and a passwordless OIDC URI. The tests remain outside the credential-free
default path.

```bash
gcloud run jobs execute matrixedmind-firestore-spike --region=REGION --wait
```

The harness also accepts a correctly formed SCRAM URI for external diagnostics, but MatrixedMind
does not use stored Firestore passwords for its Cloud Run runtime or GCP test job.

The suite deletes every document in the target `records` collection before and after each test. Use
only a dedicated non-production spike database. See
[`FIRESTORE_MONGO_SPIKE.md`](FIRESTORE_MONGO_SPIKE.md) for provisioning, required URI options, and
result-recording requirements.

The milestone 7 GCP execution passed all six Firestore compatibility tests on 2026-07-28 using the
Terraform-managed Cloud Run Job in `us-west1`.

## API tests

Use FastAPI `TestClient` or `httpx` tests for route behavior. Cover success responses, validation errors, duplicate/conflict errors, not-found responses, and repository dependency overrides.

## Web tests

Use server-rendered page tests first. Verify pages return the correct status code, render expected content, expose expected navigation, and emit expected crawler metadata. Full browser automation can wait until the UI becomes complex enough to justify it.

## Infrastructure checks

For Terraform changes:

```bash
terraform fmt -check
terraform validate
terraform plan
```

Milestone 12 operational Terraform is intentionally opt-in. Static validation must confirm that
the dev and production roots accept their default disabled alert/budget configuration and reject
enabled service-health alerting or a development budget without its required notification inputs.
A live plan or apply must not be
used as a substitute for the cloud-mutation approval gate. Once approved, verify alert policies
with a controlled test or documented manual check, validate one non-production secret rotation,
and run a restore exercise against an approved non-production target. Those hosted checks remain
unperformed until the owner confirms the project IDs and approves the audited plan.

The Cloud Run module has offline mocked Terraform tests for its exclusive `private`, `direct`, and
`external_load_balancer` invocation modes, application-project backend ownership, explicit
cross-project service-user IAM members, and invalid-input rejection. The production root separately
tests private staging, the cross-project backend contract, its required edge member, and rejection
of direct mode. The edge root tests non-disruptive DNS-authorized certificate and host-route
preparation, confirmed post-migration adoption of the existing frontend, and rejection of
unconfirmed adoption:

```bash
terraform -chdir=infra/terraform/modules/cloud_run_service init -backend=false -input=false
terraform -chdir=infra/terraform/modules/cloud_run_service test
terraform -chdir=infra/terraform/envs/prod init -backend=false -input=false
terraform -chdir=infra/terraform/envs/prod test
terraform -chdir=infra/terraform/edge init -backend=false -input=false
terraform -chdir=infra/terraform/edge test
```

For container changes:

```bash
docker build -t matrixedmind:local .
```

For CI changes, open a pull request or run the workflow through the closest supported local equivalent, then document what was actually verified.

## CI verification

`.github/workflows/ci.yml` defines the required pull-request quality gate. `CI / Required` succeeds
only when the Python quality, Docker build, and Terraform static-check jobs all pass. The Python job
starts MongoDB 8 and runs the exact milestone commands, including the full default pytest suite;
the credential-gated Firestore tests skip in that lane.

The optional Firestore workflow-dispatch job uses passwordless GitHub-to-GCP Workload Identity
Federation and invokes the dedicated Cloud Run compatibility job. It is serialized, restricted to
`main`, excluded from the required PR status, and must be requested explicitly. Its destructive
test-data rules remain those documented in [`FIRESTORE_MONGO_SPIKE.md`](FIRESTORE_MONGO_SPIKE.md).

Local workflow-equivalent verification is:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy app
docker compose up -d mongo
uv run pytest
docker build -t matrixedmind:local .
terraform fmt -check -recursive infra/
terraform -chdir=infra/terraform/bootstrap init -backend=false -input=false
terraform -chdir=infra/terraform/bootstrap validate
terraform -chdir=infra/terraform/envs/dev init -backend=false -input=false
terraform -chdir=infra/terraform/envs/dev validate
```

A local pass verifies the commands and workflow structure, but not GitHub's trigger or status
reporting. Those require a pull request run before Milestone 8 can be marked fully verified.

## Test data

Prefer small fixtures with explicit records, spaces, users, and revisions. Tests should avoid hidden dependency on execution order.

## Regression rule

Every bug fix should add a test that fails before the fix and passes after it unless the failure is purely documentation, configuration, or an external service incident.

## Documentation consistency

When behavior changes, update the relevant documentation in the same change. At minimum, route changes should update `docs/ARCHITECTURE.md` or `docs/DEVELOPMENT.md`, verification changes should update `docs/TESTING.md`, and milestone status changes should update `docs/ROADMAP.md`.
