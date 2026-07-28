# Architecture

## Application shape

MatrixedMind is a single FastAPI service serving HTML and JSON. It is a Python-first modular monolith: one deployable app, clear internal boundaries, and no separate frontend service until there is a proven need.

## Main components

- Web routes: server-rendered pages for the local personal knowledge experience in `app/web/routes/`.
- API routes: JSON endpoints for records and future automation in `app/api/routes/`. The future LLM-facing API must live behind a separate `/api/llm/*` boundary rather than exposing the normal app API to ChatGPT.
- Domain models: Python/Pydantic models in `app/domain/models.py`. The implemented models include records, revisions, users, memberships, scoped LLM tokens, and append-only audit events.
- Domain validation: reusable slug, path, title, and Markdown rules in `app/domain/validation.py`.
- Domain policy: centralized authorization and crawler/indexing helpers in `app/domain/policy.py`. Explicit rules support all five ADR 0007 principal types, deny overrides allow, and record/space/global inheritance is deterministic. Records are private and noindex by default.
- Repository interfaces: protocols in `app/domain/ports.py` used by application code.
- Storage adapters: memory and MongoDB adapters under `app/adapters/`, with future storage choices kept behind repository interfaces.
- Auth layer: `app/auth/dependencies.py` exposes a stable owner dependency, deterministic dev/test identities, fail-closed production behavior, and SHA-256 lookup of scoped, revocable LLM bearer tokens. Raw LLM tokens are never persisted.
- Import/export commands: planned portable Markdown and metadata round trips.
- GCP infrastructure: planned Terraform-managed Cloud Run, Artifact Registry, Secret Manager, Firestore Enterprise MongoDB compatibility, and supporting IAM.

## Storage strategy

Start with a local MongoDB adapter. Keep repository interfaces stable so Firestore Enterprise MongoDB compatibility, MongoDB Atlas, or another backend can be evaluated without rewriting route and domain code.

The application should depend on repository interfaces. Adapters own database-specific details such as clients, indexes, serialization, and duplicate-key handling. The MongoDB repository implements create/read/list/update behavior, creates a unique compound index for `space` and `slug`, indexes `space` and `parent_id` for child listings, converts duplicate-key failures into adapter-level `ValueError`s, and appends an embedded `RecordRevision` containing the previous Markdown body on each update.

Repository behavior is defined by reusable contract assertions under `tests/contracts/`. The unit suite applies the contract to the in-memory adapter, and the integration suite applies the same contract to MongoDB.

For the Cloud MVP, Firestore Enterprise edition with MongoDB compatibility is the preferred cloud persistence target. This must be verified by running repository contract tests against Firestore compatibility before cloud deployment is considered unblocked. Local Docker Compose MongoDB remains the local development path. MongoDB Atlas is fallback only if Firestore compatibility blocks the MVP.

The current embedded revision array is acceptable for the MVP adapter, but it should not grow unbounded long term. LLM creates and updates produce attributed revisions, while audit events are stored append-only in a separate collection.

## Cloud MVP architecture

The Cloud MVP target is:

```text
ChatGPT Custom GPT Action
        |
        | HTTPS + API key auth
        v
Cloud Run service
        |
        | app-level token validation
        v
/api/llm/* narrow write API
        |
        v
MatrixedMind repository layer
        |
        v
Firestore Enterprise MongoDB compatibility
```

ChatGPT integration enters through a constrained LLM API boundary, not the normal browser or internal record API. The initial LLM endpoints are planned as:

```text
POST /api/llm/records/upsert
GET  /api/llm/records/{space}/{slug}
GET  /api/llm/records
```

The LLM boundary is scoped, non-destructive, private/draft/noindex by default, bounded-stream body-size limited, and process-rate-limited. Tokens require an explicit owner and restrict operations and spaces. Every LLM write is attributed to `llm:chatgpt`, creates a revision, and appends an audit event. Distributed rate limiting remains a deployment-hardening concern if MatrixedMind scales beyond one Cloud Run instance.

Cloud Run filesystems are not persistent, so hosted persistence is required for deployed records, revisions, audit events, and LLM token metadata.

## Implemented routes

- `GET /health`: process health and local environment value.
- `GET /ready`: MongoDB readiness check.
- `GET /`: server-rendered home page listing records from the default space.
- `GET /{space}/{slug}`: server-rendered record detail page.
- `GET /records/new`: server-rendered new record form.
- `POST /records/new`: create a record from the browser form and redirect to the detail page.
- `GET /{space}/{slug}/edit`: server-rendered edit form.
- `POST /{space}/{slug}/edit`: update a record from the browser form and redirect to the detail page.
- `GET /api/status`: API status check.
- `POST /api/records/`: create a record with request validation aligned to the domain slug, path, title, Markdown, tag, visibility, and indexing-delay rules.
- `GET /api/records/{space}`: list records for a space, optionally by `parent_id`.
- `GET /api/records/{space}/{slug}`: read a record by space and slug.
- `PUT /api/records/{space}/{slug}`: partially update a record identified by space and slug. Supplied fields are validated with the same domain rules as create requests, then merged into the existing record before repository update. Private-to-public visibility changes set `index_after` to 7 days in the future unless an explicit override is supplied.
- `POST /api/llm/records/upsert`: scoped create/update with a deliberately fixed private, draft, and noindex policy.
- `GET /api/llm/records/{space}/{slug}`: scoped LLM record read.
- `GET /api/llm/records?space={space}`: scoped LLM record list.

Production browser identity-provider integration, import/export, and Terraform-managed deployment are not implemented yet.

## Deployment strategy

Deploy the app as a container to Cloud Run. Images are stored in Artifact Registry. Secrets are stored in Secret Manager. Infrastructure is managed with Terraform and remote state in a versioned GCS backend. GitHub Actions authenticates to GCP with Workload Identity Federation, not service-account keys.

Cloud Run may allow public unauthenticated invocation at the platform layer only after MatrixedMind enforces app-level auth for sensitive browser, internal API, and LLM API routes.

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
- No broad ChatGPT access to the internal/general API.
