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
AUTH_MODE=local
IDENTITY_PROVIDER=local
SESSION_INACTIVITY_SECONDS=2592000
SESSION_ABSOLUTE_SECONDS=7776000
SESSION_ROTATION_SECONDS=28800
OPERATOR_CREDENTIAL_TTL_SECONDS=900
AUTH_ATTEMPT_LIMIT=5
AUTH_ATTEMPT_WINDOW_SECONDS=900
AUTH_FORM_BODY_LIMIT_BYTES=16384
LLM_REQUEST_BODY_LIMIT_BYTES=65536
LLM_RATE_LIMIT_REQUESTS=60
LLM_RATE_LIMIT_WINDOW_SECONDS=60
LLM_API_SERVER_URL=
MARKDOWN_IMAGE_SOURCE_ALLOWLIST=
MONGO_ENSURE_INDEXES=true
MONGO_URI=mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?authSource=admin&replicaSet=rs0&directConnection=true&retryWrites=false
SOURCE_REPOSITORY_URL=https://github.com/MatrixedMind/MatrixedMind
SOURCE_REVISION=local
```

An empty `MARKDOWN_IMAGE_SOURCE_ALLOWLIST` permits images from any otherwise-safe external HTTPS
host. Configure a comma-separated list of exact hosts such as `images.example.com` or explicit
wildcards such as `*.usercontent.example` to restrict image rendering. Wildcards match subdomains,
not the parent domain. Image uploads and object storage are not part of this setting.

`SOURCE_REPOSITORY_URL` must identify the public HTTPS source repository. Local builds use
`SOURCE_REVISION=local` and link to that repository. Deployment image builds pass a full Git commit
SHA so the hosted link targets the matching source tree. Do not set a moving branch name as the
deployed source revision.

Local owner authentication does not use `APP_SECRET_KEY` or `LLM_TOKEN_PEPPER`: opaque browser
sessions, CSRF tokens, bootstrap credentials, and recovery credentials are random values stored
only by SHA-256 hash. The current hosted Terraform still provisions both legacy secrets. Removing
their live Secret Manager resources and IAM/environment wiring requires a separately reviewed cloud
change; do not add either value to local configuration.

## Local owner setup and recovery

`AUTH_MODE=local` is the normal local and production path. `AUTH_MODE=test` accepts an explicit
`X-Test-User-Id` only when `APP_ENV=test`; it is not a local-development shortcut. The only
implemented `IDENTITY_PROVIDER` is `local`. Firebase and OIDC are reserved adapter discriminants
and are rejected until their optional adapters exist, so clean local startup imports no provider
package and needs no provider or GCP configuration.

Start MongoDB, then issue the first-use credential from the same local environment as the app:

```bash
uv run python -m app.auth.cli bootstrap
```

The command prints one random credential once. It stores only a hash, expires after 15 minutes by
default, and cannot be used after successful setup. Open `/setup` and paste it into the form; never
put it in a URL, shell history argument, log, or configuration file. There is no default password
and setup closes permanently once an owner exists.

For operator-controlled recovery, run:

```bash
uv run python -m app.auth.cli recovery
```

Paste the printed credential into `/recovery`. A successful recovery atomically consumes the
credential, changes the password, and revokes every browser session. Normal password change at
`/settings/password` atomically changes the password and revokes every other session while leaving
the current browser signed in. Sign-out revokes the current session.

Session defaults are 30 days of inactivity, 90 days absolute lifetime, and opaque-token rotation
after eight hours of active use without re-login. `SESSION_INACTIVITY_SECONDS`,
`SESSION_ABSOLUTE_SECONDS`, `SESSION_ROTATION_SECONDS`, and
`OPERATOR_CREDENTIAL_TTL_SECONDS` configure those intervals. Session and CSRF cookies are
`HttpOnly`, `SameSite=Lax`, scoped to `/`, and `Secure` in production. Browser writes require a
session-bound CSRF token; credential forms require a strict same-origin `Origin` or `Referer`.
Login, setup, and recovery also share configurable per-process/per-client attempt limits (five
attempts per 15 minutes by default). Multi-instance hosted activation should add a shared edge or
datastore limiter before horizontal scaling.
Authentication form bodies are capped by `AUTH_FORM_BODY_LIMIT_BYTES` (16 KiB by default), and
authenticated or credential HTML responses use `Cache-Control: no-store`.

The current hosted Terraform still injects the historical `AUTH_MODE=production`, while this
application accepts `AUTH_MODE=local` or the test-only mode. Do not deploy this image to the hosted
services until Milestone 14 aligns that setting through an approved plan. Hosted activation also
requires the owner-qualified index/data migration, Firestore transaction coverage, a canonical
trusted HTTPS browser origin, and shared authentication-attempt limiting listed in the roadmap.

Production also requires `LLM_API_SERVER_URL`: the canonical public HTTPS origin that
`/openapi-llm.json` advertises to a Custom GPT Action. Leave it empty locally to derive the current
local request origin.

Milestone 7 adds an opt-in Firestore MongoDB compatibility suite without changing the local
`MONGO_URI` path. Passwordless GCP provisioning and the exact test commands are documented in
[`FIRESTORE_MONGO_SPIKE.md`](FIRESTORE_MONGO_SPIKE.md). Do not store its test-only
`FIRESTORE_MONGO_URI` in `.env` or `.env.example`.

Local MongoDB adapters create their indexes by default. Terraform manages hosted Firestore indexes,
and Cloud Run sets `MONGO_ENSURE_INDEXES=false` so the runtime service account needs data access but
not index-administration permission.

When running through Docker Compose, the `api` service uses the same database credentials with the Compose service host:

```text
MONGO_URI=mongodb://matrixed_mind:matrixed_mind@mongo:27017/matrixed_mind?authSource=admin&replicaSet=rs0&directConnection=true&retryWrites=false
```

Compose initializes an authenticated single-node `rs0` replica set and persists its generated
internal key in the `mongo_keyfile` named volume. This enables the same short record-and-audit
transactions used by the legacy automation upsert. On an existing checkout, `docker compose up`
recreates the changed MongoDB service and initializes replica-set metadata in the existing
`mongo_data` volume; it does not migrate or delete application documents. Do not use
`docker compose down -v` when preserving local data. Host-side clients use `directConnection=true`
because the replica member advertises its Compose hostname. Compose publishes MongoDB only on the
host loopback interface; the checked-in development credentials must not be used for a networked
or production database.

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

Browser and internal record routes use the local owner credential and opaque browser session.
Unauthenticated browser requests redirect to `/login`; internal record API requests return 401.
Only `APP_ENV=test` with `AUTH_MODE=test` enables the explicit `X-Test-User-Id` test seam.

The separate ChatGPT Action boundary is:

```text
GET /openapi-llm.json
POST /api/llm/records/upsert
GET /api/llm/records/{space}/{slug}
GET /api/llm/records?space={space}
```

The schema route is public and contains only the three LLM record operations. The record routes
require `Authorization: Bearer <token>`. Provision tokens through application code using
`issue_personal_access_token()`, bind every `PersonalAccessToken` to explicit `owner_id` and
`actor_id` values, and persist only `hash_personal_access_token(raw_token)`; there is intentionally
no public token-administration endpoint. See
[`CHATGPT_ACTION.md`](CHATGPT_ACTION.md) for Action configuration, manual verification, and token
rotation or revocation.

The initial server-rendered pages are:

```text
http://localhost:8000/
http://localhost:8000/source
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
