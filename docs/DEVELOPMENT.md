# Development

## Required tools

- Python 3.12
- `uv`
- Docker Desktop
- Terraform
- Google Cloud CLI
- PyCharm Pro

## Setup

```bash
uv sync --locked
docker compose up -d
uv run pytest
```

Use `.env.example` as the template for local environment variables. Do not commit `.env` or local credential files.

## Environment variables

Required local values:

```text
APP_ENV=local
AUTH_MODE=dev
LLM_REQUEST_BODY_LIMIT_BYTES=65536
LLM_RATE_LIMIT_REQUESTS=60
LLM_RATE_LIMIT_WINDOW_SECONDS=60
MONGO_ENSURE_INDEXES=true
MONGO_URI=mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?authSource=admin
```

`APP_SECRET_KEY` and `LLM_TOKEN_PEPPER` are required only when `APP_ENV=production`. The Cloud Run
service reads them from explicit Secret Manager versions. Do not add real values to `.env`,
`.env.example`, Terraform variable files, or GitHub configuration.

Milestone 7 adds an opt-in Firestore MongoDB compatibility suite without changing the local
`MONGO_URI` path. Passwordless GCP provisioning and the exact test commands are documented in
[`FIRESTORE_MONGO_SPIKE.md`](FIRESTORE_MONGO_SPIKE.md). Do not store its test-only
`FIRESTORE_MONGO_URI` in `.env` or `.env.example`.

Local MongoDB adapters create their indexes by default. Terraform manages hosted Firestore indexes,
and Cloud Run sets `MONGO_ENSURE_INDEXES=false` so the runtime service account needs data access but
not index-administration permission.

When running through Docker Compose, the `api` service uses the same database credentials with the Compose service host:

```text
MONGO_URI=mongodb://matrixed_mind:matrixed_mind@mongo:27017/matrixed_mind?authSource=admin
```

## Local app

Run the app directly:

```bash
uv run uvicorn app.main:app --reload
```

Run the app and backing services through Docker Compose:

```bash
docker compose up --build
```

The default local app URL is:

```text
http://localhost:8000
```

The health endpoint is:

```text
http://localhost:8000/health
```

The readiness endpoint verifies MongoDB connectivity:

```text
http://localhost:8000/ready
```

The JSON record routes are mounted under:

```text
http://localhost:8000/api/records
```

Implemented record API operations:

```text
POST /api/records/
GET /api/records/{space}
GET /api/records/{space}/{slug}
PUT /api/records/{space}/{slug}
```

Browser and internal record routes use the owner auth dependency. `AUTH_MODE=dev` supplies the deterministic local `dev-user`; test mode requires `X-Test-User-Id`; production requires managed runtime secrets and still fails closed until a real verified identity implementation is configured.

The separate ChatGPT Action boundary is:

```text
POST /api/llm/records/upsert
GET /api/llm/records/{space}/{slug}
GET /api/llm/records?space={space}
```

These routes require `Authorization: Bearer <token>`. Provision tokens through application code using `issue_llm_token()`, bind every `LlmApiToken` to an explicit `owner_id`, and persist only `hash_llm_token(raw_token)`; there is intentionally no public token-administration endpoint.

The initial server-rendered pages are:

```text
http://localhost:8000/
http://localhost:8000/{space}/{slug}
```

## Quality checks

Run these before considering a milestone complete:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
docker build -t matrixedmind:local .
```

`uv run pre-commit run --all-files` already runs `ruff-format` and `ruff-check` in configured hook order, so you usually do not need to run those two commands separately unless you are debugging locally or mirroring CI steps explicitly.

For infrastructure changes, also run the checks from `docs/OPERATIONS.md`.

## Continuous integration

The `CI` workflow in `.github/workflows/ci.yml` runs for pull requests targeting `main`, pushes to
`main`, and manual dispatches. Its required lanes perform the locked dependency sync, Ruff checks,
strict mypy check, full pytest suite against a MongoDB 8 service, Docker build, and credential-free
Terraform formatting and validation. The `Required` job combines those lanes into the single
`CI / Required` status intended for branch protection.

The optional Firestore compatibility lane is available only through a manual dispatch on `main`.
It uses GitHub OIDC and the Terraform-managed Workload Identity Federation provider to execute the
existing passwordless Cloud Run compatibility job. Configure these repository variables from the
applied development Terraform outputs and settings before using it:

```text
FIRESTORE_SPIKE_JOB
GCP_DEPLOYER_SERVICE_ACCOUNT
GCP_PROJECT_ID
GCP_REGION
GCP_WORKLOAD_IDENTITY_PROVIDER
```

Run it explicitly with:

```bash
gh workflow run ci.yml --ref main -f run_firestore_compatibility=true
```

The Cloud Run job deletes documents in its dedicated Firestore test collection. Do not point it at
a production database. Normal pull-request CI does not request GCP credentials.

Terraform variable files may be based on:

```text
infra/terraform/bootstrap/terraform.tfvars.example
infra/terraform/envs/dev/terraform.tfvars.example
```

Do not commit real `.tfvars` files.

## Common commands

Run a specific test file:

```bash
uv run pytest tests/unit/test_health.py
```

Format Python files:

```bash
uv run ruff format .
```

Start only local backing services:

```bash
docker compose up -d mongo
```

Stop local containers:

```bash
docker compose down
```

## PyCharm

Use the local `uv` interpreter as the primary interpreter. Use the Docker Compose interpreter only when debugging container parity. Keep inspections and commit hooks enabled.

## Development rules

- Read `docs/ROADMAP.md` before adding features.
- Build the current milestone before expanding later milestones.
- Add or update tests with implementation changes.
- Update docs in the same change when code changes routes, settings, commands, architecture boundaries, milestone status, or verification expectations.
- Keep persistence behind repository interfaces and adapters.
- Keep the server-rendered UI first unless the roadmap changes.
