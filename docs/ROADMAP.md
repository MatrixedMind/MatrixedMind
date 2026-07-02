# MatrixedMind Roadmap

## Guiding principle

Each milestone must leave the repo in a working, verifiable state. Do not stack unverified changes.

## Current focus

Milestone 4 is implemented and verified for record create, read, update, list, request validation, duplicate/not-found error handling, API docs rendering, and a manual create-read-update HTTP flow. Milestone 3 is implemented and verified for MongoDB-backed record create, read, update, list, unique slug indexes, missing-record behavior, and revision creation.

The repo already contains provisional pieces of later milestones, including an auth dependency placeholder and server-rendered pages. Treat that code as material to harden, not as permission to skip milestone verification.

## Current implementation snapshot

- `app/main.py` defines the FastAPI app, `/health`, `/ready`, API router mounting, web router mounting, and MongoDB lifespan hooks.
- `app/settings.py` loads local settings from `.env` with safe local defaults matching `.env.example`.
- `app/domain/models.py` contains `Record`, `RecordRevision`, `Space`, `Tag`, `User`, and `Membership` models.
- `app/domain/validation.py` contains slug, path, title, and Markdown validation rules.
- `app/domain/ports.py` contains the initial `RecordRepository` protocol.
- `app/adapters/memory/repository.py` contains an in-memory repository covered by the reusable repository contract.
- `app/adapters/mongo/repository.py` contains a MongoDB repository hardened against the repository contract with unique slug indexes and update revisions.
- `app/api/routes/records.py` exposes create, read, update, and list record routes with domain-aligned request schemas and consistent duplicate/not-found error handling.
- `app/web/routes/__init__.py` and `app/web/templates/` expose a minimal server-rendered home page and record detail page.
- `app/auth/dependencies.py` contains a local dev-user placeholder and a production-not-implemented branch.

## Roadmap decisions

Decision details live in `docs/DECISIONS/`. A short mapping of resolved roadmap decisions lives in `docs/ROADMAP_DECISIONS.md`.

Current ADR-backed decisions:

- FastAPI modular monolith: `docs/DECISIONS/0001-python-fastapi-modular-monolith.md`
- Storage adapter strategy: `docs/DECISIONS/0002-storage-adapter-strategy.md`
- Server-rendered UI first: `docs/DECISIONS/0003-server-rendered-ui-first.md`
- GCP Cloud Run with Terraform: `docs/DECISIONS/0004-gcp-cloud-run-terraform.md`
- Granular sharing and indexing policy model: `docs/DECISIONS/0005-granular-sharing-and-indexing-policy.md`
- Stable record identity and references: `docs/DECISIONS/0006-stable-record-identity-and-references.md`
- Detailed sharing, authorization, and indexing policy: `docs/DECISIONS/0007-sharing-authorization-and-indexing-policy.md`
- Auth modes and production requirements: `docs/DECISIONS/0008-auth-modes-and-production-requirements.md`
- Export directory format: `docs/DECISIONS/0009-export-directory-format.md`
- CI quality gate and branch protection: `docs/DECISIONS/0010-ci-quality-gate-and-branch-protection.md`
- Infrastructure layout: `docs/DECISIONS/0011-infrastructure-layout.md`
- Hosted development exposure: `docs/DECISIONS/0012-dev-hosting-exposure.md`
- Markdown rendering and sanitization: `docs/DECISIONS/0013-markdown-rendering-and-sanitization.md`

## Idea backlog

Use this section as the default landing zone for ideas that are not yet active milestone work. Move items into milestone tasks, ADRs, and architecture docs once implementation starts.

### Candidate A: Separate security for public/private spaces

**Status:** Decision direction is now resolved by ADR 0005 and ADR 0007. Implementation remains Milestone 6 work.

**Tollgate milestone:** Milestone 6.

**Implementation notes:**

- Default private behavior remains the safe baseline.
- Access checks should live in a policy/service layer, not route handlers.
- List/read behavior must filter results through the effective policy.
- Add tests for allowed and denied read/list/write behavior by visibility and membership role.

### Candidate B: Markdown rendering stack

**Status:** Resolved by ADR 0013.

**Decision:** Use `markdown-it-py` for Markdown rendering and `nh3` for sanitization behind an application-owned rendering boundary.

**Implementation notes:**

- Keep renderer calls out of route handlers and templates.
- Sanitize rendered HTML before marking it safe for templates.
- Add security fixtures for script tags, inline event handlers, unsafe URL schemes, and malformed HTML.

### Candidate C: Plugin ecosystem for custom workflows

**Status:** Not yet addressed.

**Tollgate milestone:** Finalize the extension boundary by the end of Milestone 7 before CI/deployment hardening in Milestones 8–10.

**Implementation notes:**

- Start with internal hooks first.
- Define lifecycle events and adapter interfaces before external plugin loading.
- Prefer a narrow versioned extension API with capability declarations.

### Candidate D: Stable cross-space page references with per-space unique IDs

**Status:** Decision direction is resolved by ADR 0006. Implementation remains future work.

**Tollgate milestone:** Record identity and reference contracts should be stabilized before deeper UI/auth work depends on them.

**Implementation notes:**

- Add an immutable application-level `record_id` distinct from mutable slugs and storage-native IDs.
- Resolve authored wiki links to stable IDs at save time.
- Add tests proving moves/slug changes do not break references.
- Add cross-space authorization tests so backlinks do not leak private-space metadata.

### Candidate E: Granular sharing policy and indexing/crawler controls

**Status:** Decision direction is resolved by ADR 0005 and superseded in detail by ADR 0007. Implementation remains Milestone 5 and Milestone 6 work.

**Tollgate milestone:** Baseline crawler/indexing behavior belongs in Milestone 5. Authorization behavior belongs in Milestone 6.

**Implementation notes:**

- Use explicit principal types: `user`, `organization`, `org_group`, `external_group`, and `public`.
- Evaluate `can_read`, `can_edit`, `can_share`, and `can_discover` centrally.
- Apply global → space → record policy precedence.
- Default new content to private and `noindex` until explicitly changed.
- Apply a 7-day delayed-indexing window when content changes from private to public.
- Audit policy changes with actor, target, previous value, new value, and timestamp.

---

<details>
<summary><strong>Milestone 0: Repo reset and project skeleton</strong></summary>

### Goal

Create a clean MatrixedMind repository foundation.

### Scope

- Python project metadata
- `uv` dependency lock
- `app` package
- `tests` directory
- `docs` directory
- Basic FastAPI app
- Health endpoint

### Out of scope

- Record CRUD
- Authentication
- Cloud deployment
- Production infrastructure

### Implementation tasks

#### Human intervention or decision tasks

- None.

#### AI agent implementation tasks

- [x] Keep `pyproject.toml` and `uv.lock` as the Python project source of truth.
- [x] Keep the FastAPI app entrypoint in `app/main.py`.
- [x] Keep a basic `/health` endpoint.
- [x] Keep tests under `tests/`.
- [x] Add working project docs under `docs/`.

### Verification

- [x] `uv sync --locked`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run mypy app`
- [x] `uv run pytest`
- [x] `uv run uvicorn app.main:app --reload`
- [x] `curl http://localhost:8000/health`

### Done when

A clean FastAPI skeleton runs locally and all checks pass.

</details>

---

<details>
<summary><strong>Milestone 1: Local development stack</strong></summary>

### Goal

Run MatrixedMind locally with Dockerized backing services.

### Scope

- `compose.yaml`
- Local MongoDB container
- Settings management
- `.env.example`
- Database connection health check

### Out of scope

- Cloud database provisioning
- Production authentication
- Full record CRUD
- Import/export

### Implementation tasks

#### Human intervention or decision tasks

- None.

#### AI agent implementation tasks

- [x] Keep a Docker Compose stack for the app and MongoDB.
- [x] Keep local settings in `app/settings.py`.
- [x] Keep `.env.example` as the local configuration template.
- [x] Add a database-aware health check or readiness check.
- [x] Add an integration test that proves the app can connect to local MongoDB.
- [x] Document required local environment variables in `docs/DEVELOPMENT.md`.

### Verification

- [x] `docker compose up -d`
- [x] `docker compose ps`
- [x] `uv run pytest tests/integration`
- [x] `curl http://localhost:8000/health`
- [x] `curl http://localhost:8000/ready`
- [x] MongoDB connectivity is confirmed by an integration test and readiness endpoint.

### Done when

A developer can clone the repo, run Compose, and verify the app talks to its local backing service.

</details>

---

<details>
<summary><strong>Milestone 2: Domain model and repository interfaces</strong></summary>

### Goal

Define the core MatrixedMind data model before building more UI features.

### Scope

- `Record`
- `RecordRevision`
- `Space`
- `Tag`
- `User`
- `Membership`
- Repository protocols/interfaces
- Slug and path rules

### Out of scope

- Final visual design
- Production auth provider
- Cloud persistence choice
- Search indexing

### Implementation tasks

#### Human intervention or decision tasks

- [x] Add or explicitly defer `Space`, `Tag`, `User`, and `Membership` models.

#### AI agent implementation tasks

- [x] Define initial `Record` and `RecordRevision` models.
- [x] Define an initial record repository protocol.
- [x] Define slug, path, title, and Markdown validation rules.
- [x] Add repository contract tests that can run against memory and Mongo adapters.
- [x] Remove mutable default values from domain models where needed.

### Verification

- [x] Unit tests for model validation.
- [x] Unit tests for slug and path rules.
- [x] Repository contract tests pass against the in-memory adapter.
- [x] `uv run mypy app`
- [x] `uv run pytest tests/unit`

### Done when

The domain model is stable enough to support CRUD and storage adapters.

</details>

---

<details>
<summary><strong>Milestone 3: MongoDB storage adapter</strong></summary>

### Goal

Persist and retrieve Markdown-first records locally.

### Scope

- MongoDB repository implementation
- Record create/read/update/list
- Revision creation
- Basic indexes
- Adapter-level error handling

### Out of scope

- Firestore implementation
- Full-text search
- Import/export
- Production backup automation

### Implementation tasks

#### Human intervention or decision tasks

- None.

#### AI agent implementation tasks

- [x] Harden the MongoDB repository implementation against the repository contract.
- [x] Add create, read, update, and list behavior for records.
- [x] Ensure updates create revisions.
- [x] Add unique indexes for `space` and `slug`.
- [x] Add tests for duplicate slugs and missing records.

### Verification

- [x] Integration test creates a record.
- [x] Integration test updates a record and creates a revision.
- [x] Integration test lists records by space and parent.
- [x] Repository contract tests pass against MongoDB.
- [x] `uv run pytest tests/integration`

### Done when

The app can round-trip real MatrixedMind records through MongoDB.

</details>

---

<details>
<summary><strong>Milestone 4: API layer</strong></summary>

### Goal

Expose stable JSON endpoints for records.

### Scope

- Create record endpoint
- Read record endpoint
- Update record endpoint
- List records endpoint
- API schemas
- Error responses

### Out of scope

- Public API versioning
- API tokens
- Search API
- Bulk import API

### Implementation tasks

#### Human intervention or decision tasks

- None.

#### AI agent implementation tasks

- [x] Add initial create, read, and list routes.
- [x] Add update record route.
- [x] Align API schemas with the domain validation rules.
- [x] Return consistent 400, 404, and validation responses.
- [x] Add route tests for happy paths and invalid payloads.

### Verification

- [x] FastAPI route tests pass.
- [x] Invalid payloads return correct errors.
- [x] API docs render at `/docs`.
- [x] Manual curl/httpie create-read-update flow works.
- [x] `uv run pytest tests/unit tests/integration`

### Done when

The API can manage records end-to-end against local storage.

</details>

---

<details>
<summary><strong>Milestone 5: Web UI shell</strong></summary>

### Goal

Add a minimal browser-facing interface.

### Scope

- Base layout
- Home page
- Record detail page
- Record editor page
- Simple navigation
- Server-rendered Markdown display
- Effective crawler/indexing metadata

### Out of scope

- Separate React SPA
- Rich collaborative editor
- Advanced theming
- Full browser automation suite

### Implementation tasks

#### Human intervention or decision tasks

- [x] Finalize the robots/indexing metadata model with precedence rules (global → space → record). See ADR 0007.
- [x] Add delayed-indexing defaults for newly public content and document override behavior. See ADR 0007.

#### AI agent implementation tasks

- [x] Add initial server-rendered routes and templates.
- [ ] Add a base layout shared by pages.
- [ ] Add a record editor page.
- [ ] Add create/edit form handling.
- [x] Render Markdown content safely. See ADR 0013.
- [ ] Add simple navigation between home, list, detail, and editor views.

### Verification

- [ ] Page tests return 200.
- [ ] HTML renders expected record content.
- [ ] Public pages emit expected crawler/indexing metadata from effective policy.
- [ ] Visibility flips to `public` do not become indexable before the configured delay window.
- [ ] Manual browser test can create, edit, and view a record.
- [ ] `uv run pytest`

### Done when

MatrixedMind is usable as a very rough local wiki.

</details>

---

<details>
<summary><strong>Milestone 6: Auth foundation</strong></summary>

### Goal

Separate local/dev auth from future production auth.

### Scope

- Auth interface
- Dev auth mode
- Session/user dependency
- Protected routes
- User identity model alignment
- Policy-aware read/list/write behavior

### Out of scope

- Final hosted identity provider
- Full multi-tenant implementation
- Password storage
- Shared-secret production shortcut

### Implementation tasks

#### Human intervention or decision tasks

- [x] Finalize principal model for sharing (`user`, `organization`, `org_group`, `external_group`, `public`). See ADR 0007.
- [x] Finalize authorization policy contract (`can_read`, `can_edit`, `can_share`, `can_discover`) with documented allow/deny precedence. See ADR 0007.
- [x] Document production auth requirements before selecting a provider. See ADR 0008.

#### AI agent implementation tasks

- [ ] Define an auth dependency boundary.
- [ ] Add a dev user mode for local work.
- [ ] Protect record write routes.
- [ ] Add user context to record creation and revisions.
- [ ] Add policy-aware filtering so list/read queries only return discoverable resources.

### Verification

- [ ] Unauthenticated requests are rejected or redirected.
- [ ] Dev user can access protected routes.
- [ ] Tests cover allowed and denied cases.
- [ ] Tests cover share scenarios for each principal type and verify precedence behavior.
- [ ] Cross-space reference and backlink queries do not leak private-space metadata.
- [ ] `uv run pytest`

### Done when

The app has real auth boundaries without committing to final production auth yet.

</details>

---

<details>
<summary><strong>Milestone 7: Import/export</strong></summary>

### Goal

Keep MatrixedMind portable and recoverable.

### Scope

- Export records to Markdown plus JSON metadata
- Import records from an export directory
- CLI command or script
- Round-trip tests

### Out of scope

- Live sync
- Third-party importers
- Scheduled backups
- Binary asset management

### Implementation tasks

#### Human intervention or decision tasks

- [x] Define an export directory format. See ADR 0009.

#### AI agent implementation tasks

- [ ] Export records and revisions.
- [ ] Import exported records idempotently.
- [ ] Add a CLI command or script entrypoint.
- [ ] Add fixture-based round-trip tests.

### Verification

- [ ] Export fixture data.
- [ ] Delete the local database.
- [ ] Import exported data.
- [ ] Confirm records and revisions match expected values.
- [ ] `uv run pytest`

### Done when

Content is not trapped inside the current database.

</details>

---

<details>
<summary><strong>Milestone 8: CI quality gate</strong></summary>

### Goal

Make every PR automatically verifiable.

### Scope

- GitHub Actions CI workflow
- `uv sync`
- Ruff
- mypy
- pytest
- Docker build

### Out of scope

- Production deployment
- Terraform apply
- Release automation
- Browser automation unless added by earlier milestones

### Implementation tasks

#### Human intervention or decision tasks

- [x] Document required branch protection expectations. See ADR 0010.

#### AI agent implementation tasks

- [ ] Add a GitHub Actions workflow.
- [ ] Cache `uv` dependencies safely.
- [ ] Run lint, format check, type check, and tests.
- [ ] Build the Docker image.

### Verification

- [ ] Open PR triggers CI.
- [ ] CI fails on lint, type, test, or Docker build failure.
- [ ] CI passes on a clean branch.

### Done when

No code merges without automated verification.

</details>

---

<details>
<summary><strong>Milestone 9: Terraform bootstrap</strong></summary>

### Goal

Prepare GCP infrastructure safely.

### Scope

- Terraform bootstrap stack
- GCS backend bucket
- Artifact Registry
- Cloud Run service account
- Secret Manager placeholder secrets
- Workload Identity Federation resources

### Out of scope

- Production traffic cutover
- Custom domain
- CDN
- Multi-region deployment

### Implementation tasks

#### Human intervention or decision tasks

- [x] Define Terraform roots in `infra/terraform/envs/{dev,prod}`. See ADR 0011.

#### AI agent implementation tasks

- [ ] Define reusable modules in `infra/terraform/modules/*`.
- [ ] Configure GCS backend with versioning.
- [ ] Add Artifact Registry.
- [ ] Add Cloud Run service account.
- [ ] Add placeholder Secret Manager secrets.
- [ ] Add GitHub Actions Workload Identity Federation.

### Verification

- [ ] `terraform fmt -check`
- [ ] `terraform validate`
- [ ] `terraform plan`
- [ ] State is stored in the GCS backend.

### Done when

GCP infrastructure can be planned repeatably from Terraform.

</details>

---

<details>
<summary><strong>Milestone 10: Dev Cloud Run deployment</strong></summary>

### Goal

Deploy the first working MatrixedMind container to GCP.

### Scope

- Docker image build
- Push to Artifact Registry
- Cloud Run deployment
- Secret injection
- Health endpoint check
- Intentional service exposure

### Out of scope

- Production launch
- Custom domain
- Autoscaling optimization
- Advanced observability

### Implementation tasks

#### Human intervention or decision tasks

- [x] Document whether the dev service is public or private. See ADR 0012.

#### AI agent implementation tasks

- [ ] Build a production Docker image in CI.
- [ ] Push the image to Artifact Registry.
- [ ] Deploy Cloud Run through Terraform or an intentional deployment workflow.
- [ ] Inject secrets from Secret Manager.
- [ ] Add post-deploy health verification.

### Verification

- [ ] GitHub Actions authenticates to GCP via OIDC.
- [ ] Image is pushed to Artifact Registry.
- [ ] Terraform deploys Cloud Run.
- [ ] Cloud Run health endpoint responds.
- [ ] Service exposure is intentional and documented.

### Done when

MatrixedMind has a working dev deployment on GCP.

</details>
