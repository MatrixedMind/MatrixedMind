# MatrixedMind Roadmap

## Guiding principle

Each milestone must leave the repo in a working, verifiable state. Do not stack unverified changes.

## Current focus

Milestone 4 is implemented and verified for record create, read, update, list, request validation, duplicate/not-found error handling, API docs rendering, and a manual create-read-update HTTP flow. Milestone 3 is implemented and verified for MongoDB-backed record create, read, update, list, unique slug indexes, missing-record behavior, and revision creation.

Milestone 5 remains the current implementation focus. The roadmap now pulls the secure Cloud MVP path forward after Milestone 5: owner auth and the LLM write API, Firestore MongoDB compatibility verification, CI, Cloud Run deployment, ChatGPT Action integration, and cloud hardening. Import/export is deferred until after that secure cloud path unless recovery needs pull it forward.

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
- Cloud MVP with Firestore MongoDB compatibility and ChatGPT Action: `docs/DECISIONS/0014-cloud-mvp-firestore-mongo-and-chatgpt-action.md`

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

**Tollgate milestone:** Deferred until after the secure Cloud MVP path.

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
- [x] Add a base layout shared by pages.
- [x] Add a record editor page.
- [x] Add create/edit form handling.
- [x] Render Markdown content safely. See ADR 0013.
- [ ] Add simple navigation between home, list, detail, and editor views.

### Verification

- [x] Page tests return 200.
- [x] HTML renders expected record content.
- [ ] Public pages emit expected crawler/indexing metadata from effective policy.
- [ ] Visibility flips to `public` do not become indexable before the configured delay window.
- [ ] Manual browser test can create, edit, and view a record.
- [ ] `uv run pytest`

### Done when

MatrixedMind is usable as a very rough local personal knowledge app.

</details>

---

<details>
<summary><strong>Milestone 6: MVP auth and LLM write API</strong></summary>

### Goal

Enforce owner authentication for browser/internal routes and add a narrow, scoped LLM write API for ChatGPT.

### Scope

- Auth interface
- Owner auth boundary
- Dev auth mode
- Token auth mode
- LLM API token model
- Narrow `/api/llm/*` endpoints
- Synthetic LLM actor attribution
- Private/draft/noindex LLM write defaults
- Revisions and audit events for LLM writes
- Protected routes
- User identity model alignment
- Policy-aware read/list/write behavior

### Out of scope

- Final hosted identity provider
- Full multi-tenant implementation
- Password storage
- Shared-secret production shortcut
- OAuth
- MCP
- Public publishing
- Destructive LLM tools
- Bulk import through the LLM API

### Implementation tasks

#### Human intervention or decision tasks

- [x] Finalize principal model for sharing (`user`, `organization`, `org_group`, `external_group`, `public`). See ADR 0007.
- [x] Finalize authorization policy contract (`can_read`, `can_edit`, `can_share`, `can_discover`) with documented allow/deny precedence. See ADR 0007.
- [x] Document production auth requirements before selecting a provider. See ADR 0008.
- [x] Decide first ChatGPT integration path. Use Custom GPT Actions with API key authentication. See ADR 0014.
- [x] Decide LLM API capability boundary. Keep it narrow, scoped, separate, and non-destructive. See ADR 0014.

#### AI agent implementation tasks

- [ ] Define an owner auth dependency boundary.
- [ ] Add a dev user mode for local work.
- [ ] Add a token auth mode for LLM API requests.
- [ ] Add an LLM API token model.
- [ ] Store only hashed LLM tokens.
- [ ] Add token scopes for allowed operations.
- [ ] Limit tokens to allowed spaces.
- [ ] Add token revocation.
- [ ] Protect record write routes.
- [ ] Add user context to record creation and revisions.
- [ ] Add policy-aware filtering so list/read queries only return discoverable resources.
- [ ] Attribute LLM writes to a synthetic actor such as `llm:chatgpt`.
- [ ] Add `POST /api/llm/records/upsert`.
- [ ] Add `GET /api/llm/records/{space}/{slug}`.
- [ ] Add `GET /api/llm/records`.
- [ ] Default LLM-created records to private, draft, and noindex.
- [ ] Ensure every LLM write creates a revision.
- [ ] Ensure every LLM write creates an audit event.
- [ ] Add LLM API rate limits.
- [ ] Add LLM API body size limits.
- [ ] Reject LLM attempts to delete records.
- [ ] Reject LLM attempts to publish records.
- [ ] Reject LLM attempts to change visibility.
- [ ] Reject LLM attempts to change indexing policy.
- [ ] Reject LLM attempts to change sharing policy.
- [ ] Reject LLM attempts to change auth settings.
- [ ] Reject LLM admin actions.
- [ ] Reject LLM bulk import.

### Verification

- [ ] Unauthenticated requests are rejected or redirected.
- [ ] Dev user can access protected routes.
- [ ] Tests cover allowed and denied cases.
- [ ] Tests cover share scenarios for each principal type and verify precedence behavior.
- [ ] Cross-space reference and backlink queries do not leak private-space metadata.
- [ ] Tests prove allowed LLM reads and writes work inside allowed spaces.
- [ ] Tests prove forbidden LLM behavior is rejected.
- [ ] Tests prove revoked LLM tokens fail.
- [ ] Tests prove LLM writes create revisions and audit events.
- [ ] `uv run pytest`

### Done when

MatrixedMind has real auth boundaries and a narrow LLM write API without committing to final browser production auth provider details.

</details>

---

<details>
<summary><strong>Milestone 7: Firestore Mongo compatibility spike</strong></summary>

### Goal

Prove whether Firestore Enterprise MongoDB compatibility can be the cloud persistence target.

### Scope

- Firestore Enterprise database setup documentation
- Firestore MongoDB compatibility connection settings
- Repository contract tests against Firestore compatibility
- Unique index verification
- `ObjectId` verification
- `DuplicateKeyError` behavior verification
- `update_one` / `$set` behavior verification
- Sorting verification
- Readiness check verification
- MongoDB Atlas fallback note

### Out of scope

- Cloud Run deployment
- Production traffic
- Import/export
- Rewriting repository code before the compatibility result is known

### Implementation tasks

#### Human intervention or decision tasks

- [x] Prefer Firestore Enterprise MongoDB compatibility as the cloud database target, pending tests. See ADR 0014.
- [x] Keep local Docker Compose MongoDB as the local development path. See ADR 0014.
- [x] Keep MongoDB Atlas as fallback only if Firestore compatibility blocks the MVP. See ADR 0014.

#### AI agent implementation tasks

- [ ] Document Firestore Enterprise database setup steps for the spike.
- [ ] Document Firestore MongoDB compatibility connection settings, including `loadBalanced=true`, `SCRAM-SHA-256`, `tls=true`, and `retryWrites=false`.
- [ ] Add a way to run repository contract tests against Firestore MongoDB compatibility without replacing local MongoDB development.
- [ ] Verify unique compound index behavior.
- [ ] Verify `ObjectId` behavior.
- [ ] Verify duplicate key errors map to expected adapter behavior.
- [ ] Verify `update_one` with `$set`.
- [ ] Verify sorting behavior.
- [ ] Verify readiness checks.
- [ ] Document any adapter changes required for compatibility.
- [ ] Record fallback criteria for MongoDB Atlas if Firestore compatibility fails.

### Verification

- [ ] Repository contract tests pass against local MongoDB.
- [ ] Repository contract tests pass against Firestore MongoDB compatibility, or exact blockers are documented.
- [ ] Unique index, `ObjectId`, duplicate key, `$set`, sorting, and readiness behavior are verified.
- [ ] `uv run pytest`

### Done when

Firestore MongoDB compatibility is either verified for the current repository contract or blocked with exact fallback criteria for MongoDB Atlas.

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
- [ ] Run `uv sync --locked`.
- [ ] Cache `uv` dependencies safely.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run mypy app`.
- [ ] Run `uv run pytest`.
- [ ] Build the Docker image.
- [ ] Add an optional integration test job for local MongoDB and Firestore compatibility when credentials are available.

### Verification

- [ ] Open PR triggers CI.
- [ ] CI fails on lint, type, test, or Docker build failure.
- [ ] CI passes on a clean branch.

### Done when

No code merges without automated verification.

</details>

---

<details>
<summary><strong>Milestone 9: Cloud deployment baseline</strong></summary>

### Goal

Deploy MatrixedMind to Cloud Run with hosted persistence and managed secrets.

### Scope

- Docker image build
- Artifact Registry
- Cloud Run service
- Secret Manager integration
- Firestore Enterprise Mongo-compatible connection
- Runtime service account
- Health/readiness checks
- Cloud Run environment and secret configuration
- Deployment docs

### Out of scope

- Production traffic cutover
- Custom domain
- CDN
- Multi-region deployment
- ChatGPT Custom GPT setup
- Public Cloud Run invocation before app-level auth is enforced

### Implementation tasks

#### Human intervention or decision tasks

- [x] Define Terraform roots in `infra/terraform/envs/{dev,prod}`. See ADR 0011.
- [x] Use Cloud Run, Artifact Registry, Secret Manager, and Workload Identity Federation for the Cloud MVP path. See ADR 0004 and ADR 0014.
- [x] Allow public Cloud Run invocation only after app-level auth is enforced. See ADR 0014.

#### AI agent implementation tasks

- [ ] Define reusable modules in `infra/terraform/modules/*`.
- [ ] Configure GCS backend with versioning.
- [ ] Add Artifact Registry.
- [ ] Build the Docker image.
- [ ] Add Cloud Run service.
- [ ] Add runtime service account.
- [ ] Add Secret Manager integration for runtime secrets.
- [ ] Configure Firestore Enterprise Mongo-compatible connection through secrets/configuration.
- [ ] Configure Cloud Run environment variables and secret mounts.
- [ ] Add health and readiness checks for the deployed service.
- [ ] Add GitHub Actions Workload Identity Federation.
- [ ] Document deployment commands and manual setup steps.
- [ ] Confirm public Cloud Run invocation is enabled only after app-level auth protects sensitive routes.

### Verification

- [ ] `terraform fmt -check`
- [ ] `terraform validate`
- [ ] `terraform plan`
- [ ] Docker image builds.
- [ ] Image is pushed to Artifact Registry.
- [ ] Cloud Run deploys.
- [ ] Runtime secrets are read from Secret Manager.
- [ ] Cloud Run health endpoint responds.
- [ ] Cloud Run readiness endpoint verifies hosted persistence.
- [ ] Service exposure is intentional and documented.

### Done when

MatrixedMind has a working Cloud Run deployment baseline with managed runtime secrets and hosted persistence wiring.

</details>

---

<details>
<summary><strong>Milestone 10: ChatGPT Action integration</strong></summary>

### Goal

Connect ChatGPT to MatrixedMind through a narrow Custom GPT Action.

### Scope

- `/openapi-llm.json`
- LLM-only OpenAPI schema
- Custom GPT Action setup guide
- Manual ChatGPT test checklist
- Token rotation/revocation guide
- Allowed and forbidden behavior tests
- Smoke test through deployed Cloud Run URL

### Out of scope

- OAuth
- MCP
- ChatGPT Apps SDK
- Destructive LLM capabilities
- Full internal API exposure
- Public publishing

### Implementation tasks

#### Human intervention or decision tasks

- [x] Use Custom GPT Actions with API key authentication for the first LLM integration. See ADR 0014.
- [x] Keep the LLM API separate from the internal/general API. See ADR 0014.

#### AI agent implementation tasks

- [ ] Add `/openapi-llm.json`.
- [ ] Generate an LLM-only OpenAPI schema.
- [ ] Ensure the schema exposes only the allowed `/api/llm/*` endpoints.
- [ ] Write the Custom GPT Action setup guide.
- [ ] Write the manual ChatGPT test checklist.
- [ ] Write the token rotation and revocation guide.
- [ ] Add tests proving allowed LLM behavior.
- [ ] Add tests proving forbidden LLM behavior.
- [ ] Smoke test create/update through the deployed Cloud Run URL.

### Verification

- [ ] `/openapi-llm.json` returns only LLM-safe operations.
- [ ] Custom GPT Action can create or update a private draft record.
- [ ] Custom GPT Action cannot delete, publish, change sharing, change indexing, change auth, or write outside allowed spaces.
- [ ] LLM token revocation blocks later requests.
- [ ] Smoke test passes through the deployed Cloud Run URL.
- [ ] `uv run pytest`

### Done when

ChatGPT can use a Custom GPT Action to create or update private draft records through the deployed MatrixedMind service without gaining broad or destructive access.

</details>

---

<details>
<summary><strong>Milestone 11: Cloud hardening</strong></summary>

### Goal

Harden the Cloud MVP before trusting it with higher-sensitivity personal knowledge.

### Scope

- Alerting
- Log review
- Backup/restore validation
- Billing budget alerts
- Secret rotation procedure
- Rate-limit tuning
- Firestore cost review
- Static egress/private connectivity review if needed
- Custom domain decision

### Out of scope

- Polished UI
- Full multi-user sharing UI
- Public publishing
- Plugin infrastructure
- Import/export unless pulled forward by recovery requirements

### Implementation tasks

#### Human intervention or decision tasks

- [ ] Decide whether a custom domain is needed before broader use.
- [ ] Decide whether static egress or private connectivity is needed.

#### AI agent implementation tasks

- [ ] Configure alerting for service health and error rates.
- [ ] Document log review workflow.
- [ ] Validate backup and restore assumptions.
- [ ] Configure billing budget alerts.
- [ ] Document secret rotation procedure.
- [ ] Tune rate limits based on LLM API smoke-test behavior.
- [ ] Review Firestore document-size and index-write costs.
- [ ] Document static egress/private connectivity tradeoffs if needed.

### Verification

- [ ] Alerts fire in a controlled test or documented manual check.
- [ ] Restore procedure is validated or exact blocker is recorded.
- [ ] Billing budget alerts are configured.
- [ ] Secret rotation checklist is tested with a non-production token.
- [ ] Firestore cost review is documented.

### Done when

The Cloud MVP has the operational guardrails needed for cautious personal use.

</details>

---

## Later work

These items remain deferred until after the secure Cloud MVP path is working:

- Import/export implementation from ADR 0009.
- Full multi-user auth and sharing UI.
- Public publishing.
- OAuth integration.
- MCP integration.
- Plugin infrastructure.
- Custom domain implementation unless Milestone 11 pulls the decision forward.
- Polished UI.
