# MatrixedMind Roadmap

## Guiding principle

Each milestone must leave the repo in a working, verifiable state. Do not stack unverified changes.

## Current focus

Finish Milestone 1 verification against the local Docker Compose stack, then normalize the Milestone 2 domain model and repository contracts. The repo already contains provisional pieces of later milestones, including records, MongoDB, API routes, and server-rendered pages. Treat that code as material to harden, not as permission to skip milestone verification.

---

## Milestone 0: Repo reset and project skeleton

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

---

## Milestone 1: Local development stack

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

- [x] Keep a Docker Compose stack for the app and MongoDB.
- [x] Keep local settings in `app/settings.py`.
- [x] Keep `.env.example` as the local configuration template.
- [ ] Add a database-aware health check or readiness check.
- [ ] Add an integration test that proves the app can connect to local MongoDB.
- [ ] Document required local environment variables in `docs/DEVELOPMENT.md`.

### Verification

- [ ] `docker compose up -d`
- [ ] `docker compose ps`
- [ ] `uv run pytest tests/integration`
- [ ] `curl http://localhost:8000/health`
- [ ] MongoDB connectivity is confirmed by an integration test or readiness endpoint.

### Done when

A developer can clone the repo, run Compose, and verify the app talks to its local backing service.

---

## Milestone 2: Domain model and repository interfaces

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

- [x] Define initial `Record` and `RecordRevision` models.
- [x] Define an initial record repository protocol.
- [ ] Add or explicitly defer `Space`, `Tag`, `User`, and `Membership` models.
- [ ] Define slug, path, title, and Markdown validation rules.
- [ ] Add repository contract tests that can run against memory and Mongo adapters.
- [ ] Remove mutable default values from domain models where needed.

### Verification

- [ ] Unit tests for model validation.
- [ ] Unit tests for slug and path rules.
- [ ] Repository contract tests pass against the in-memory adapter.
- [ ] `uv run mypy app`
- [ ] `uv run pytest tests/unit`

### Done when

The domain model is stable enough to support CRUD and storage adapters.

---

## Milestone 3: MongoDB storage adapter

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

- [ ] Harden the MongoDB repository implementation against the repository contract.
- [ ] Add create, read, update, and list behavior for records.
- [ ] Ensure updates create revisions.
- [ ] Add unique indexes for `space` and `slug`.
- [ ] Add tests for duplicate slugs and missing records.

### Verification

- [ ] Integration test creates a record.
- [ ] Integration test updates a record and creates a revision.
- [ ] Integration test lists records by space and parent.
- [ ] Repository contract tests pass against MongoDB.
- [ ] `uv run pytest tests/integration`

### Done when

The app can round-trip real MatrixedMind records through MongoDB.

---

## Milestone 4: API layer

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

- [x] Add initial create, read, and list routes.
- [ ] Add update record route.
- [ ] Align API schemas with the domain validation rules.
- [ ] Return consistent 400, 404, and validation responses.
- [ ] Add route tests for happy paths and invalid payloads.

### Verification

- [ ] FastAPI route tests pass.
- [ ] Invalid payloads return correct errors.
- [ ] API docs render at `/docs`.
- [ ] Manual curl/httpie create-read-update flow works.
- [ ] `uv run pytest tests/unit tests/integration`

### Done when

The API can manage records end-to-end against local storage.

---

## Milestone 5: Web UI shell

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

- [x] Add initial server-rendered routes and templates.
- [ ] Add a base layout shared by pages.
- [ ] Add a record editor page.
- [ ] Add create/edit form handling.
- [ ] Render Markdown content safely.
- [ ] Add simple navigation between home, list, detail, and editor views.

### Verification

- [ ] Page tests return 200.
- [ ] HTML renders expected record content.
- [ ] Manual browser test can create, edit, and view a record.
- [ ] `uv run pytest`

### Done when

MatrixedMind is usable as a very rough local wiki.

---

## Milestone 6: Auth foundation

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

- [ ] Define an auth dependency boundary.
- [ ] Add a dev user mode for local work.
- [ ] Protect record write routes.
- [ ] Add user context to record creation and revisions.
- [ ] Document production auth requirements before selecting a provider.

### Verification

- [ ] Unauthenticated requests are rejected or redirected.
- [ ] Dev user can access protected routes.
- [ ] Tests cover allowed and denied cases.
- [ ] `uv run pytest`

### Done when

The app has real auth boundaries without committing to final production auth yet.

---

## Milestone 7: Import/export

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

- [ ] Define an export directory format.
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

---

## Milestone 8: CI quality gate

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

- [ ] Add a GitHub Actions workflow.
- [ ] Cache `uv` dependencies safely.
- [ ] Run lint, format check, type check, and tests.
- [ ] Build the Docker image.
- [ ] Document required branch protection expectations.

### Verification

- [ ] Open PR triggers CI.
- [ ] CI fails on lint, type, test, or Docker build failure.
- [ ] CI passes on a clean branch.

### Done when

No code merges without automated verification.

---

## Milestone 9: Terraform bootstrap

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

- [ ] Define Terraform roots in `infra/terraform/envs/{dev,prod}`.
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

---

## Milestone 10: Dev Cloud Run deployment

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

- [ ] Build a production Docker image in CI.
- [ ] Push the image to Artifact Registry.
- [ ] Deploy Cloud Run through Terraform or an intentional deployment workflow.
- [ ] Inject secrets from Secret Manager.
- [ ] Document whether the dev service is public or private.
- [ ] Add post-deploy health verification.

### Verification

- [ ] GitHub Actions authenticates to GCP via OIDC.
- [ ] Image is pushed to Artifact Registry.
- [ ] Terraform deploys Cloud Run.
- [ ] Cloud Run health endpoint responds.
- [ ] Service exposure is intentional and documented.

### Done when

MatrixedMind has a working dev deployment on GCP.
