# Architecture

## Application shape

MatrixedMind is a single FastAPI service serving HTML and JSON. It is a Python-first modular monolith: one deployable app, clear internal boundaries, and no separate frontend service until there is a proven need.

## Main components

- Web routes: server-rendered pages for the local wiki experience in `app/web/routes/`.
- API routes: JSON endpoints for records and future automation in `app/api/routes/`.
- Domain models: Python/Pydantic models in `app/domain/models.py`. The current implemented models are `Record`, `RecordRevision`, `Space`, `Tag`, `User`, and `Membership`.
- Domain validation: reusable slug, path, title, and Markdown rules in `app/domain/validation.py`.
- Repository interfaces: protocols in `app/domain/ports.py` used by application code.
- Storage adapters: memory and MongoDB adapters under `app/adapters/`, with future storage choices kept behind repository interfaces.
- Auth layer: local/dev auth placeholder in `app/auth/dependencies.py`; production auth is intentionally not implemented yet.
- Import/export commands: planned portable Markdown and metadata round trips.
- GCP infrastructure: planned Terraform-managed Cloud Run, Artifact Registry, Secret Manager, and supporting IAM.

## Storage strategy

Start with a local MongoDB adapter. Keep repository interfaces stable so Firestore, Firestore Mongo compatibility, or another backend can be added later without rewriting route and domain code.

The application should depend on repository interfaces. Adapters own database-specific details such as clients, indexes, serialization, and duplicate-key handling. The current MongoDB repository is provisional: basic create/read/list/update methods exist, but Milestone 3 still needs contract hardening, unique indexes, revision behavior, and adapter-level error handling.

Repository behavior is defined by reusable contract assertions under `tests/contracts/`. Milestone 2 applies the contract to the in-memory adapter; Milestone 3 should apply the same contract to MongoDB.

## Implemented routes

- `GET /health`: process health and local environment value.
- `GET /ready`: MongoDB readiness check.
- `GET /`: server-rendered home page listing records from the default space.
- `GET /{space}/{slug}`: server-rendered record detail page.
- `GET /api/status`: API status check.
- `POST /api/records/`: create a record.
- `GET /api/records/{space}`: list records for a space, optionally by `parent_id`.
- `GET /api/records/{space}/{slug}`: read a record by space and slug.

No update API route, record editor page, production auth flow, import/export command, or Terraform-managed deployment is implemented yet.

## Deployment strategy

Deploy the app as a container to Cloud Run. Images are stored in Artifact Registry. Secrets are stored in Secret Manager. Infrastructure is managed with Terraform and remote state in a versioned GCS backend. GitHub Actions authenticates to GCP with Workload Identity Federation, not service-account keys.

## Local development strategy

Local development should work without GCP credentials for core features. Docker Compose provides backing services, including MongoDB. The FastAPI app can also run directly with `uv run uvicorn app.main:app --reload`.

## Boundary rules

- Domain models must not import FastAPI route modules.
- Route handlers should depend on repository interfaces or dependencies, not concrete database clients.
- Storage adapters must not define web or API behavior.
- Infrastructure code must not require application imports.
- Tests should verify behavior at the lowest useful layer before adding broader tests.

## Non-goals for now

- No separate React SPA.
- No multiservice architecture.
- No premature multi-tenant design.
- No production auth shortcut using shared secrets.
- No cloud-only development loop.
- No database-specific assumptions outside adapters.
