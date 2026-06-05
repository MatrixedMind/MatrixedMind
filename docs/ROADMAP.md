# MatrixedMind Roadmap

## Guiding principle

Each milestone must leave the repo in a working, verifiable state. Do not stack unverified changes.

## Current focus

Milestone 4 is implemented and verified for record create, read, update, list, request validation, duplicate/not-found error handling, API docs rendering, and a manual create-read-update HTTP flow. Milestone 3 is implemented and verified for MongoDB-backed record create, read, update, list, unique slug indexes, missing-record behavior, and revision creation. The repo already contains provisional pieces of later milestones, including an auth dependency placeholder and server-rendered pages. Treat that code as material to harden, not as permission to skip milestone verification.

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

## Idea backlog (research notes)

<details>
<summary><strong>Expand idea backlog</strong></summary>

Use this section as the default landing zone for new ideas that are not yet active milestone work. Move items into milestone tasks, ADRs, and architecture docs once implementation starts.

### Candidate A: Separate security for public/private spaces

**Status:** Not yet addressed for application-level spaces (separate from Milestone 10 service exposure).

**Tollgate milestone:** Finalize by the end of Milestone 6 (Auth foundation) so later API/UI behavior does not bake in incompatible access rules.

**Research notes:**

- Common FOSS wiki patterns use a space-level visibility flag (`public` or `private`) plus role-based membership (owner/editor/viewer).
- The lowest-risk default is deny-by-default for private spaces, with explicit grants through membership records.
- A practical policy boundary is read/write authorization in a service layer, not directly in route handlers.
- Data filtering should happen at query time (list/read endpoints return only records from spaces the caller can access).

**Suggested spike scope:**

- Add a provisional `SpaceVisibility` field and a minimal policy matrix in the domain layer.
- Add authz-focused tests for allowed and denied read/list/write behavior by visibility and membership role.
- Record final policy decisions in a dedicated ADR before broader multi-user work.

### Candidate B: Evaluate FOSS Markdown rendering stack

**Status:** Partially addressed only as a roadmap requirement to "render Markdown content safely"; tool choice is still open.

**Tollgate milestone:** Finalize by the end of Milestone 5 (Web UI shell) to avoid reworking templates, sanitization behavior, and content tests.

**Research notes:**

- `markdown-it-py` has an active ecosystem, CommonMark compatibility, and plugin support for tables, task lists, and footnotes.
- `python-markdown` is mature and widely used, with many extensions, but extension quality and behavior vary.
- `mistune` is fast and flexible, but extension coverage can require more custom wiring.
- For untrusted content, pair rendering with strict sanitization (`nh3` or equivalent allowlist sanitizer) and explicit URL scheme rules.

**Suggested spike scope:**

- Build a small renderer adapter interface and compare at least two engines (`markdown-it-py` and `python-markdown`) behind that boundary.
- Validate output against security-focused fixtures (script tags, inline event handlers, `javascript:` links, malformed HTML).
- Capture chosen stack and allowlist rules in `docs/SECURITY.md` and an ADR.

### Candidate C: Plugin ecosystem for custom workflows

**Status:** Not yet addressed.

**Tollgate milestone:** Finalize the extension boundary by the end of Milestone 7 (Import/export), before CI/deployment hardening in Milestones 8–10.

**Research notes:**

- Successful plugin ecosystems usually start with a narrow, versioned extension API and capability-based permissions.
- In-process arbitrary code plugins are easy for local use but increase security and upgrade risk for hosted deployments.
- A safer early path is "internal hooks first": define lifecycle events and adapter interfaces before opening external plugin loading.
- Compatibility guidance from FOSS ecosystems suggests semantic API versioning, deprecation windows, and contract tests for extension points.

**Suggested spike scope:**

- Define a provisional extension surface (for example - Markdown preprocessing, post-save automation, export format adapters).
- Add a plugin manifest schema with declared capabilities and minimum API version.
- Start with built-in adapters that use the same API as external plugins, then decide on the loading model (local package vs. an isolated process) in a later milestone.

### Candidate D: Stable cross-space page references with per-space unique IDs

**Status:** Not yet addressed.

**Tollgate milestone:** Finalize by the end of Milestone 4 (API layer) so record identity and reference contracts are stable before broader UI and auth work.

**Research notes:**

- Wiki and docs systems usually separate immutable identity from mutable location: a stable record ID plus a changeable path/slug.
- Keeping links resilient during page moves typically requires references to target the stable ID, with path/slug used only for display and routing.
- Cross-space references are usually modeled as explicit link objects (`from_record_id`, `to_record_id`) so permissions and backlink queries are enforceable.
- Human-friendly authoring is typically implemented via autocomplete/search mention syntax that resolves to IDs at save time.

**Suggested spike scope:**

- Add a per-space immutable `record_id` (for example, ULID-style) distinct from `slug` and `parent_id`.
- Define a canonical reference syntax that can resolve by lookup without memorizing paths, then store normalized links by ID.
- Add move tests that prove parent changes do not invalidate references and backlink queries still resolve.
- Add cross-space authorization tests to ensure that references do not leak private-space metadata.

### Candidate E: Granular sharing policy and indexing/crawler controls

**Status:** Not yet addressed.

**Tollgate milestone:** Finalize the authorization model by the end of Milestone 6 (Auth foundation), with baseline crawler/indexing behavior defined by the end of Milestone 5 (Web UI shell).

**Research notes:**

- Mature collaboration systems usually separate identity and policy: principals (user, org, group, public) are modeled independently of resource rules.
- Security policy is easier to evolve when effective access is computed from additive allow rules plus explicit denies, with clear conflict resolution documented.
- Multi-level metadata controls are common for crawler behavior: global defaults, then space-level overrides, then record-level overrides.
- A delayed-indexing safety window is a practical mitigation for accidental exposure, but it should be paired with explicit `noindex` defaults and audit logs for visibility changes.

**Suggested spike scope:**

- Define principals and scopes explicitly: user, organization, org group, external group, and public.
- Add a policy evaluation contract (`can_read`, `can_edit`, `can_share`, `can_discover`) with tests for inheritance, override precedence, and deny cases.
- Add metadata controls for robots and automation policy at global, space, and record levels (for example: `index`, `follow`, `archive`, `ai_training`, `automated_browsing`).
- Add a configurable indexing delay (for example: `index_after`) that defaults to a non-zero hold period when visibility changes from private to public.
- Add event/audit records for sharing and indexing policy changes, including actor, target, previous value, new value, and timestamp.

**Design suggestions to reduce future refactors:**

- Keep authorization and crawler policy checks in a dedicated service layer, not in route handlers or templates.
- Store policy as explicit structured fields, not free-text flags embedded in Markdown front matter.
- Apply "secure by default" posture: private by default, `noindex` by default, explicit publish action required for public indexing.
- Reserve explicit handling for outbound surfaces beyond search crawlers (export APIs, feeds, embeddings, plugin callbacks) so the same policy model governs all data egress.

</details>

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

### Out of scope

- Separate React SPA
- Rich collaborative editor
- Advanced theming
- Full browser automation suite

### Implementation tasks

#### Human intervention or decision tasks

- [ ] Finalize the robots/indexing metadata model with precedence rules (global → space → record).
- [ ] Add delayed-indexing defaults for newly public content and document override behavior.

#### AI agent implementation tasks

- [x] Add initial server-rendered routes and templates.
- [ ] Add a base layout shared by pages.
- [ ] Add a record editor page.
- [ ] Add create/edit form handling.
- [ ] Render Markdown content safely.
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

### Out of scope

- Final hosted identity provider
- Multi-tenant authorization model
- Password storage
- Shared-secret production shortcut

### Implementation tasks

#### Human intervention or decision tasks

- [ ] Finalize principal model for sharing (`user`, `organization`, `org_group`, `external_group`, `public`).
- [ ] Finalize authorization policy contract (`can_read`, `can_edit`, `can_share`, `can_discover`) with documented allow/deny precedence.
- [ ] Document production auth requirements before selecting a provider.

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

- [ ] Define an export directory format.

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

- [ ] Document required branch protection expectations.

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

- [ ] Define Terraform roots in `infra/terraform/envs/{dev,prod}`.

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

- [ ] Document whether the dev service is public or private.

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
