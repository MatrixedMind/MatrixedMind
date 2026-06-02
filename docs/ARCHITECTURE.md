# Architecture

## Application shape

MatrixedMind is a single FastAPI service serving HTML and JSON. It is a Python-first modular monolith: one deployable app, clear internal boundaries, and no separate frontend service until there is a proven need.

## Main components

- Web routes: server-rendered pages for the local wiki experience.
- API routes: JSON endpoints for records and future automation.
- Domain models: Python/Pydantic models that describe MatrixedMind concepts.
- Repository interfaces: stable protocols used by application code.
- Storage adapters: MongoDB first, with future storage choices kept behind repository interfaces.
- Auth layer: local/dev auth first, production auth selected later behind a dependency boundary.
- Import/export commands: portable Markdown and metadata round trips.
- GCP infrastructure: Terraform-managed Cloud Run, Artifact Registry, Secret Manager, and supporting IAM.

## Storage strategy

Start with a local MongoDB adapter. Keep repository interfaces stable so Firestore, Firestore Mongo compatibility, or another backend can be added later without rewriting route and domain code.

The application should depend on repository interfaces. Adapters own database-specific details such as clients, indexes, serialization, and duplicate-key handling.

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
