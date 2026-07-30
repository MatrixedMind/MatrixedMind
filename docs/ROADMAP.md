# MatrixedMind Roadmap

## Guiding principle

Each milestone must leave the repo in a working, verifiable state. Do not stack unverified changes.

## Current focus

Milestone 4 is implemented and verified for record create, read, update, list, request validation, duplicate/not-found error handling, API docs rendering, and a manual create-read-update HTTP flow. Milestone 3 is implemented and verified for MongoDB-backed record create, read, update, list, unique slug indexes, missing-record behavior, and revision creation.

Milestone 5 is implemented and verified for a minimal server-rendered browser shell, shared layout, home/detail/editor pages, create/edit form handling, simple navigation, safe Markdown rendering, private/noindex defaults, and delayed indexing for public records.

Milestone 6 is implemented and verified for owner auth boundaries, deterministic dev/test identities, centralized authorization policy, hashed/scoped/revocable LLM tokens, narrow private-by-default LLM record operations, revision and audit attribution, request limits, and forbidden capability handling.

Milestones 0 through 7 and Milestones 9 and 10 are implemented and verified, including Firestore
Enterprise MongoDB compatibility, the Cloud Run deployment baseline, and the narrow ChatGPT Action
integration. Milestone 8's CI quality gate is
implemented and passes clean pull requests; its deliberate-failure verification remains open. The
current focus is Milestone 11 hosted activation, followed by Milestone 12 cloud operational
hardening and Milestone 13 public project documentation. Import/export is deferred until after that
secure cloud path unless recovery needs pull it forward.

The repo already contains provisional pieces of later milestones, including an auth dependency placeholder and server-rendered pages. Treat that code as material to harden, not as permission to skip milestone verification.

## Current implementation snapshot

- `app/main.py` defines the FastAPI app, `/health`, `/ready`, API router mounting, web router mounting, and MongoDB lifespan hooks.
- `app/settings.py` loads local settings from `.env` with safe local defaults matching `.env.example`.
- `app/domain/models.py` contains `Record`, `RecordRevision`, `Space`, `Tag`, `User`, and `Membership` models.
- `app/domain/validation.py` contains slug, path, title, and Markdown validation rules.
- `app/domain/policy.py` contains provisional crawler/indexing metadata helpers with private/noindex defaults and a 7-day public indexing delay.
- `app/domain/ports.py` contains the initial `RecordRepository` protocol.
- `app/adapters/memory/repository.py` contains an in-memory repository covered by the reusable repository contract.
- `app/adapters/mongo/repository.py` contains a MongoDB repository hardened against the repository contract with unique slug indexes and update revisions.
- `app/api/routes/records.py` exposes create, read, update, and list record routes with domain-aligned request schemas and consistent duplicate/not-found error handling.
- `app/web/routes/__init__.py` and `app/web/templates/` expose a minimal server-rendered home page, record detail page, record editor pages, and browser form handling.
- `app/auth/dependencies.py` contains the stable owner auth boundary, deterministic dev/test identities, fail-closed production behavior, hashed LLM bearer-token authentication, and process-local rate limiting.
- `app/api/routes/llm.py` exposes narrow scoped LLM record upsert, read, and list operations with private/draft/noindex defaults, revision attribution, and append-only audit events.

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
- Hosted and self-hosted deployment modes: `docs/DECISIONS/0015-hosted-and-self-hosted-deployment-modes.md`
- Official public documentation mirror: `docs/DECISIONS/0016-official-public-documentation-mirror.md`
- External Markdown image policy: `docs/DECISIONS/0017-external-markdown-image-policy.md`

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
- [x] Add simple navigation between home, list, detail, and editor views.

### Verification

- [x] Page tests return 200.
- [x] HTML renders expected record content.
- [x] Public pages emit expected crawler/indexing metadata from effective policy.
- [x] Visibility flips to `public` do not become indexable before the configured delay window.
- [x] Manual browser test can create, edit, and view a record.
- [x] `uv run pytest`

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

- [x] Define an owner auth dependency boundary.
- [x] Add a dev user mode for local work.
- [x] Add a token auth mode for LLM API requests.
- [x] Add an LLM API token model.
- [x] Store only hashed LLM tokens.
- [x] Add token scopes for allowed operations.
- [x] Limit tokens to allowed spaces.
- [x] Add token revocation.
- [x] Protect record write routes.
- [x] Add user context to record creation and revisions.
- [x] Add policy-aware filtering so list/read queries only return discoverable resources.
- [x] Attribute LLM writes to a synthetic actor such as `llm:chatgpt`.
- [x] Add `POST /api/llm/records/upsert`.
- [x] Add `GET /api/llm/records/{space}/{slug}`.
- [x] Add `GET /api/llm/records`.
- [x] Default LLM-created records to private, draft, and noindex.
- [x] Ensure every LLM write creates a revision.
- [x] Ensure every LLM write creates an audit event.
- [x] Add LLM API rate limits.
- [x] Add LLM API body size limits.
- [x] Reject LLM attempts to delete records.
- [x] Reject LLM attempts to publish records.
- [x] Reject LLM attempts to change visibility.
- [x] Reject LLM attempts to change indexing policy.
- [x] Reject LLM attempts to change sharing policy.
- [x] Reject LLM attempts to change auth settings.
- [x] Reject LLM admin actions.
- [x] Reject LLM bulk import.

### Verification

- [x] Unauthenticated requests are rejected or redirected.
- [x] Dev user can access protected routes.
- [x] Tests cover allowed and denied cases.
- [x] Tests cover share scenarios for each principal type and verify precedence behavior.
- [x] Cross-space reads do not leak private-space metadata; backlink queries are not implemented.
- [x] Tests prove allowed LLM reads and writes work inside allowed spaces.
- [x] Tests prove forbidden LLM behavior is rejected.
- [x] Tests prove revoked LLM tokens fail.
- [x] Tests prove LLM writes create revisions and audit events.
- [x] `uv run pytest`

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

- [x] Document Firestore Enterprise database setup steps for the spike.
- [x] Document Firestore MongoDB compatibility connection settings, including passwordless GCP OIDC, `loadBalanced=true`, `tls=true`, and `retryWrites=false`; retain SCRAM only for external diagnostics.
- [x] Add a way to run repository contract tests against Firestore MongoDB compatibility without replacing local MongoDB development.
- [x] Verify unique compound index behavior.
- [x] Verify `ObjectId` behavior.
- [x] Verify duplicate key errors map to expected adapter behavior.
- [x] Verify `update_one` with `$set`.
- [x] Verify sorting behavior.
- [x] Verify readiness checks.
- [x] Document any adapter changes required for compatibility.
- [x] Record fallback criteria for MongoDB Atlas if Firestore compatibility fails.

### Verification

- [x] Repository contract tests pass against local MongoDB.
- [x] Repository contract tests pass against Firestore MongoDB compatibility, or exact blockers are documented.
- [x] Unique index, `ObjectId`, duplicate key, `$set`, sorting, and readiness behavior are verified.
- [x] `uv run pytest`

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

- [x] Add a GitHub Actions workflow.
- [x] Run `uv sync --locked`.
- [x] Cache `uv` dependencies safely.
- [x] Run `uv run ruff check .`.
- [x] Run `uv run ruff format --check .`.
- [x] Run `uv run mypy app`.
- [x] Run `uv run pytest`.
- [x] Build the Docker image.
- [x] Add an optional integration test job for local MongoDB and Firestore compatibility when credentials are available.

### Verification

- [x] Open PR triggers CI.
- [ ] CI fails on lint, type, test, or Docker build failure.
- [x] CI passes on a clean branch.

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

- [x] Define reusable modules in `infra/terraform/modules/*`.
- [x] Configure GCS backend with versioning.
- [x] Add Artifact Registry.
- [x] Build the Docker image.
- [x] Add Cloud Run service.
- [x] Add runtime service account.
- [x] Add Secret Manager integration for runtime secrets.
- [x] Configure Firestore Enterprise Mongo-compatible connection through secrets/configuration.
- [x] Configure Cloud Run environment variables and secret mounts.
- [x] Add health and readiness checks for the deployed service.
- [x] Add GitHub Actions Workload Identity Federation.
- [x] Document deployment commands and manual setup steps.
- [x] Confirm public Cloud Run invocation is enabled only after app-level auth protects sensitive routes.

### Verification

- [x] `terraform fmt -check`
- [x] `terraform validate`
- [x] `terraform plan`
- [x] Docker image builds.
- [x] Image is pushed to Artifact Registry.
- [x] Cloud Run deploys.
- [x] Runtime secrets are read from Secret Manager.
- [x] Cloud Run health endpoint responds.
- [x] Cloud Run readiness endpoint verifies hosted persistence.
- [x] Service exposure is intentional and documented.

### Done when

MatrixedMind has a working Cloud Run deployment baseline with managed runtime secrets and hosted persistence wiring.

</details>

---

<details>
<summary><strong>Milestone 10: ChatGPT Action integration</strong></summary>

### Goal

Prepare MatrixedMind to connect to ChatGPT through a narrow Custom GPT Action after the change is
deployed from `main`.

### Scope

- `/openapi-llm.json`
- LLM-only OpenAPI schema
- Custom GPT Action setup guide
- Manual ChatGPT test checklist
- Token rotation/revocation guide
- Allowed and forbidden behavior tests
- Deployment and activation handoff to Milestone 11

### Out of scope

- OAuth
- MCP
- ChatGPT Apps SDK
- Destructive LLM capabilities
- Full internal API exposure
- Public publishing
- Activating the Custom GPT against the deployed Cloud Run service

### Implementation tasks

#### Human intervention or decision tasks

- [x] Use Custom GPT Actions with API key authentication for the first LLM integration. See ADR 0014.
- [x] Keep the LLM API separate from the internal/general API. See ADR 0014.

#### AI agent implementation tasks

- [x] Add `/openapi-llm.json`.
- [x] Generate an LLM-only OpenAPI schema.
- [x] Ensure the schema exposes only the allowed `/api/llm/*` endpoints.
- [x] Write the Custom GPT Action setup guide.
- [x] Write the manual ChatGPT test checklist.
- [x] Write the token rotation and revocation guide.
- [x] Add tests proving allowed LLM behavior.
- [x] Add tests proving forbidden LLM behavior.

### Verification

- [x] `/openapi-llm.json` returns only LLM-safe operations.
- [x] LLM token revocation blocks later requests.
- [x] `uv run pytest`

### Done when

MatrixedMind exposes a tested LLM-only Action schema, documents secure Custom GPT configuration and
token rotation, and is ready for deployed activation without exposing broad or destructive access.

</details>

---

<details>
<summary><strong>Milestone 11: Hosted activation</strong></summary>

### Goal

Make the secure Cloud MVP usable through its custom domain and a narrow private ChatGPT Action.

### Scope

- Custom GPT activation
- Custom-domain routing through the shared external load balancer
- Cloud Run ingress restricted to the load balancer when that deployment mode is selected
- Deployed LLM API smoke testing
- Optional OpenAI ChatGPT-integration IP allowlist for the Action API host
- AGPL source-offer link for the hosted interface
- Safe rendering of externally hosted Markdown images, with optional image-source allowlists

### Out of scope

- Polished UI
- Full multi-user sharing UI
- Public publishing
- Plugin infrastructure
- Import/export unless pulled forward by recovery requirements

### Implementation tasks

#### Human intervention or decision tasks

- [x] Use a custom domain for the hosted MatrixedMind deployment.
- [x] Use separate shared-edge, private-development, and production-application projects. Reuse the
  existing shared external load balancer and static IP through global cross-project service
  referencing without Shared VPC; keep direct public Cloud Run as a separate self-hosted mode. See
  ADR 0015.
- [x] Enable the hosted load-balancer invocation path only after the deployed revision includes the
  narrow LLM schema and app-level token enforcement, without enabling direct public Cloud Run.
- [x] Configure a private Custom GPT Action with a dedicated scoped MatrixedMind token.

#### AI agent implementation tasks

- [x] Smoke test create and update through the deployed Cloud Run URL.
- [x] Verify deployed reads and writes cannot escape the token's allowed spaces.
- [x] Verify the deployed API exposes no delete, publish, sharing, indexing, auth, admin, or bulk
  import capability to the Custom GPT.
- [x] Revoke the deployed test token and verify later requests fail.
- [x] Configure the custom-domain load-balancer route and Cloud Run ingress for the selected
  deployment mode. See ADR 0015.
- [x] Add optional OpenAI ChatGPT-integration IP allowlist support to the Action API host, with a
  reviewed refresh process for changes to the published range feed; leave it disabled unless the
  operator opts into Cloud Armor Enterprise and supplies a reviewed address group.
- [x] Add a visible AGPL source-offer link and license notice to the hosted interface, pointing to
  the corresponding public source for the deployed version.
- [x] Safely render externally hosted HTTPS images in Markdown while preserving only required image
  attributes, rejecting unsafe URL schemes, raw HTML, event handlers, and inline styles, and
  enforcing optional configured image-source allowlists. See ADR 0017.

### Verification

- [x] `/openapi-llm.json` is reachable through the custom domain while sensitive routes still
  require app-level authentication.
- [x] Custom GPT Action can create or update a private draft record.
- [x] Custom GPT Action cannot delete, publish, change sharing, change indexing, change auth, or
  write outside allowed spaces.
- [x] LLM token revocation blocks later deployed requests.
- [x] Smoke test passes through the deployed Cloud Run URL.
- [x] The selected custom-domain routing and Cloud Run ingress mode work without exposing an
  unintended direct public path.
- [ ] When the optional Action API allowlist is enabled, it accepts current ChatGPT integration
  requests and rejects an unapproved source.
- [x] The hosted interface offers the corresponding source for its deployed version.
- [x] Approved HTTPS Markdown images render, while malicious image markup and unsafe URLs are
  removed or neutralized.

### Done when

The Cloud MVP is available through its intended deployment mode, supports the narrow private
ChatGPT Action, and includes the baseline hosted-interface safety controls.

</details>

---

<details>
<summary><strong>Milestone 12: Cloud operational hardening</strong></summary>

### Goal

Add the operational guardrails needed before MatrixedMind is trusted with higher-sensitivity
personal knowledge or sustained use.

### Scope

- Alerting and log review
- Backup and restore validation
- Billing budget alerts
- Secret rotation procedure
- Rate-limit tuning
- Firestore cost review
- Static egress or private-connectivity review when required

### Out of scope

- New product capabilities
- Public documentation publishing
- Image uploads and object storage

### Implementation tasks

#### Human intervention or decision tasks

- [x] Decide whether static egress or private connectivity is needed for an external dependency.
  None is currently needed; revisit when a dependency requires fixed-IP allowlisting or private
  networking.
- [x] Select and approve the authentication approach for read-only Google Cloud MCP access.
  Use dedicated keyless, read-only observer service accounts, preferably one per environment,
  through ADC/service-account impersonation; exact service-account identities and IAM roles still
  require the audited cloud-mutation plan.
- [ ] Confirm which development and production projects the observer may inspect.
  Proposed for the final audited plan: `matrixed-mind-dev` and `matrixedmind-prod`; the shared-edge
  project remains excluded. This is an approval of live scope, not a separate identifier request.
- [x] Decide whether HashiCorp's Terraform MCP server runs as a pinned local binary or pinned
  container image. Use a pinned, checksum-verified local binary unless HashiCorp has no supported
  local artifact.
- [x] Require explicit approval before enabling Google Cloud MCP services or granting associated
  IAM roles. Approval is required before every live cloud mutation; repository configuration and
  read-only discovery are authorized now.

#### AI agent implementation tasks

- [ ] Configure alerting for service health and error rates.
- [x] Document log review workflow.
- [ ] Validate backup and restore assumptions.
- [ ] Configure billing budget alerts.
- [ ] Document and test a secret rotation procedure with a non-production token.
- [ ] Tune rate limits based on deployed LLM API behavior.
- [ ] Review Firestore document-size and index-write costs.
- [x] Document static egress/private connectivity tradeoffs if needed.
- [ ] Extend `gcp_docs_researcher` with HashiCorp's official Terraform MCP server, pinned to a
  reviewed version or immutable container digest. Enable only public Terraform Registry
  documentation tools: `search_providers` and `get_provider_details`; allow
  `get_latest_provider_version` only when comparison requires it. Keep the repository lock file
  authoritative for the version in use, inspect `.terraform.lock.hcl`, retrieve locked-version
  provider documentation whenever possible, and keep credentials out of the repository. Do not
  enable HCP Terraform, Terraform Enterprise, workspace-management, run-management, or mutation
  tools.
- [ ] Add read-only `matrixedmind_gcp_observer` for bounded MatrixedMind health, logs, metrics,
  alerts, and Cloud Run service-metadata investigations. Require an explicit project, environment,
  time range, and investigation objective; return concise summaries rather than raw log dumps; do
  not edit repository files, mutate GCP resources, change IAM, deploy, create credentials, or
  expose secrets or sensitive log contents.
- [ ] Scope observer MCP access to Cloud Logging `list_log_entries` and `list_log_names`; Cloud
  Monitoring `list_timeseries`, `query_range`, `get_alert_policy`, `list_alert_policies`,
  `get_alert`, `list_alerts`, `list_metric_descriptors`, and optional read-only dashboard tools;
  and, only if needed, Cloud Run `get_service` and `list_services`. Do not enable Cloud Run
  deployment, Firestore mutation, Cloud CLI Execution, IAM, or other mutation tools. Use both MCP
  tool allowlists and least-privilege Google IAM; neither replaces the other.
- [ ] Keep Terraform documentation and GCP observer MCP servers scoped only to the agents that
  need them. Use narrow log filters, short time windows, explicit limits, and one project per
  query; retrieve only sufficient evidence, sanitize examples, and stop rather than repeatedly
  polling unchanged hosted state. Distinguish supported behavior documented by MCP research from
  deployed state shown by live read-only MCP results.

### Verification

- [ ] Alerts fire in a controlled test or documented manual check.
- [ ] Restore procedure is validated or exact blocker is recorded.
- [ ] Billing budget alerts are configured.
- [ ] Secret rotation checklist is tested with a non-production token.
- [ ] Firestore cost review is documented.
- [ ] New TOML files parse successfully.
- [ ] The Terraform MCP exposes only approved public Registry documentation tools, and a
  version-specific provider lookup matches the repository's locked Google provider version.
- [ ] The observer exposes only approved read-only tools; mutating Cloud Run, Firestore, Cloud
  CLI, IAM, deployment, and Terraform workspace tools are absent.
- [ ] A bounded development-project smoke test reads a known Cloud Run service, a narrow log
  window, and relevant monitoring metadata without changing hosted state.
- [ ] Source-controlled files contain no API keys, access tokens, ADC files, OAuth secrets,
  service-account JSON, or generated credentials.
- [ ] Any unavailable authentication, API enablement, IAM grant, or live verification is recorded
  as an exact manual blocker rather than marked complete.

### Current implementation status

Repository-only operational configuration and procedures are in progress. Alert policies, billing
budgets, and their conventional Terraform-managed notification channels are disabled by default;
no project IDs, notification channels, billing accounts, APIs, IAM roles, service accounts, alerts,
budgets, secret rotations, or restore operations have been created or changed for Milestone 12.
The single remaining manual blocker is approval of the audited cloud-mutation plan. It asks only
for the notification destination and development/production budget amounts; it recommends routine
identifiers, the two proposed observer projects, and the isolated development restore target.

### Done when

The hosted service has documented, tested operational safeguards for cautious sustained use,
authoritative version-aware Terraform provider research, a tested least-privilege read-only
workflow for diagnosing hosted MatrixedMind state, and proof that mutating MCP tools are
unavailable to the observer.

</details>

---

<details>
<summary><strong>Milestone 13: Public project documentation</strong></summary>

### Goal

Use MatrixedMind to mirror official MatrixedMind Markdown documentation in a public-facing site
without weakening the private personal-knowledge workflow or enabling public docs by default for
self-hosted instances.

### Scope

- A dedicated public documentation space that is disabled by default
- An explicitly configured official documentation source, separate from the self-hosted default
- A deliberate, reviewed workflow that mirrors the configured Markdown documentation source
- Deterministic translation of repository-relative Markdown links to public documentation records
- Stable public documentation URLs and navigation
- Crawler metadata appropriate for deliberately public documentation
- Tests proving public documentation cannot expose private records or protected functionality

### Out of scope

- Arbitrary public publishing for all users
- Automatic publishing on every source-repository change
- Public API access
- Full-text search
- Multi-user sharing UI

### Implementation tasks

#### Human intervention or decision tasks

- [ ] Confirm the official public documentation source and the publishing review policy.

#### AI agent implementation tasks

- [ ] Add a safe workflow for mirroring and unpublishing documentation records in the dedicated
  public space. See ADR 0016.
- [ ] Add public documentation navigation and stable record URLs.
- [ ] Translate supported repository-relative Markdown links to the matching public documentation
  records and detect links whose source target cannot be mirrored. See ADR 0016.
- [ ] Add tests for public read access, private-record isolation, and protected-route isolation.
- [ ] Document the manual documentation-mirror publishing workflow and its opt-in configuration.
  See ADR 0016.

### Verification

- [ ] A visitor can read the approved public documentation without an account.
- [ ] Private records, drafts, edit routes, internal APIs, and LLM APIs remain unavailable to an
  unauthenticated visitor.
- [ ] Public documentation emits the intended crawler metadata.
- [ ] The publication guide identifies the configured source and shows that a default self-hosted
  instance has no public documentation source enabled.

### Done when

MatrixedMind mirrors its configured official documentation source in a small, tested public site
while private knowledge and privileged application capabilities remain isolated.

</details>

---

## Later work

These items remain deferred until after the secure Cloud MVP path is working:

- Import/export implementation from ADR 0009.
- Full multi-user auth and sharing UI.
- General public publishing beyond the dedicated documentation site.
- OAuth integration.
- MCP integration.
- Plugin infrastructure.
- Additional custom domains beyond the Milestone 11 hosted activation domain.
- Polished UI.
- Automatic repository-to-MatrixedMind documentation publishing.
