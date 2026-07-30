# Architecture

## Application shape

MatrixedMind is a single FastAPI service serving HTML and JSON. It is a Python-first modular monolith: one deployable app, clear internal boundaries, and no separate frontend service until there is a proven need.

## Main components

- Web routes: server-rendered pages for the local personal knowledge experience in `app/web/routes/`.
- API routes: JSON endpoints for records and future automation in `app/api/routes/`. The future LLM-facing API must live behind a separate `/api/llm/*` boundary rather than exposing the normal app API to ChatGPT.
- Domain models: Python/Pydantic models in `app/domain/models.py`. The implemented models include records, revisions, users, memberships, scoped LLM tokens, and append-only audit events.
- Domain validation: reusable slug, path, title, and Markdown rules in `app/domain/validation.py`.
- Rendering boundary: `app/rendering.py` renders Markdown and sanitizes HTML. It permits external
  images only over HTTPS, applies an optional exact-host or wildcard-host source allowlist, and
  preserves only `src`, `alt`, and `title` on approved images.
- Domain policy: centralized authorization and crawler/indexing helpers in `app/domain/policy.py`. Explicit rules support all five ADR 0007 principal types, deny overrides allow, and record/space/global inheritance is deterministic. Records are private and noindex by default.
- Repository interfaces: protocols in `app/domain/ports.py` used by application code.
- Storage adapters: memory and MongoDB adapters under `app/adapters/`, with future storage choices kept behind repository interfaces.
- Auth layer: `app/auth/dependencies.py` exposes a stable owner dependency, deterministic dev/test identities, fail-closed production behavior, and SHA-256 lookup of scoped, revocable LLM bearer tokens. Raw LLM tokens are never persisted.
- Import/export commands: planned portable Markdown and metadata round trips.
- GCP infrastructure: Terraform-managed Cloud Run, Artifact Registry, Secret Manager, Firestore Enterprise MongoDB compatibility, and supporting IAM. Reusable modules live under `infra/terraform/modules/`; development and production roots remain separate.

## Storage strategy

Start with a local MongoDB adapter. Keep repository interfaces stable so Firestore Enterprise MongoDB compatibility, MongoDB Atlas, or another backend can be evaluated without rewriting route and domain code.

The application should depend on repository interfaces. Adapters own database-specific details such as clients, serialization, and duplicate-key handling. Local MongoDB adapters create indexes by default. In GCP, Terraform owns index creation and the adapters run with `MONGO_ENSURE_INDEXES=false`, keeping index-administration permissions away from the application runtime. The MongoDB repository implements create/read/list/update behavior, converts duplicate-key failures into adapter-level `ValueError`s, and appends an embedded `RecordRevision` containing the previous Markdown body on each update.

Repository behavior is defined by reusable contract assertions under `tests/contracts/`. The unit suite applies the contract to the in-memory adapter, and the integration suite applies the same contract to MongoDB.

The opt-in suite under `tests/firestore/` applies that same contract plus explicit checks for
compound uniqueness, `ObjectId`, duplicate-key mapping, `$set` updates, sorting, and readiness. It
uses a separate `FIRESTORE_MONGO_URI`; the default application and test configuration remains local
MongoDB.

For the Cloud MVP, Firestore Enterprise edition with MongoDB compatibility is the preferred cloud persistence target. This must be verified by running repository contract tests against Firestore compatibility before cloud deployment is considered unblocked. Local Docker Compose MongoDB remains the local development path. MongoDB Atlas is fallback only if Firestore compatibility blocks the MVP.

Cloud Run and the GCP compatibility-test job authenticate to Firestore with their attached service
accounts through `MONGODB-OIDC`. Terraform derives the passwordless URI from the Firestore database
resource and grants only `roles/datastore.user`; no database password is stored in Secret Manager or
Terraform state.

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
- `GET /source`: public AGPLv3 notice and corresponding-source link with restrictive crawler
  metadata and no record content.
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

`GET /openapi-llm.json` is the public integration contract for the Custom GPT Action. MatrixedMind
generates it from only the `/api/llm/*` routes, attaches deterministic Action operation IDs and
bearer-token security to every operation, identifies a configured canonical production origin as
the Action server, and excludes the internal API, browser routes, health routes, and unavailable
destructive or administrative capabilities.

Production browser identity-provider integration and import/export are not implemented yet. The Terraform-managed deployment baseline is implemented, but the first Cloud Run application deployment still requires owner-run infrastructure and deployment verification.

The shared web layout includes the AGPLv3 notice and a source-offer link. Deployment images built by
the development workflow embed the verified Git commit so that the link targets the corresponding
source revision rather than a moving branch.

## Deployment strategy

Deploy the app as a container to Cloud Run. Images are stored in Artifact Registry. Secrets are stored in Secret Manager and injected at explicit versions. Infrastructure is managed with Terraform and remote state in a versioned GCS backend. GitHub Actions authenticates to GCP with Workload Identity Federation, builds immutable commit-tagged images, deploys verified `main` revisions, and checks process health plus hosted-persistence readiness.

Cloud Run may allow public unauthenticated invocation at the platform layer only after MatrixedMind enforces app-level auth for sensitive browser, internal API, and LLM API routes.

The Cloud Run module uses one exclusive invocation-mode value. `private` preserves the restricted
staging baseline, `direct` is the lower-cost direct public mode for self-hosters, and
`external_load_balancer` grants platform invocation while restricting ingress to internal and Cloud
Load Balancing traffic. The last mode creates the serverless NEG and backend service beside Cloud
Run in the application project. It outputs the fully qualified backend reference but does not create
or modify a load-balancer frontend, static IP, certificate, URL map, or DNS record.

The official hosted topology separates a shared edge project, a private development project, and a
production application project. The production backend uses same-organization cross-project
service referencing from a global external Application Load Balancer without Shared VPC.
`infra/terraform/edge` owns the DNS-authorized certificates, SNI certificate map, host routes,
proxies, and the adopted `EXTERNAL_MANAGED` backend and forwarding rules while retaining the shared
static IP. The deployed production Cloud Run service accepts traffic from Cloud Load Balancing but
does not expose a working direct public `run.app` path. Operators enrolled in Cloud Armor
Enterprise can optionally attach a policy that restricts only `/api/llm/*` through a reviewed
ChatGPT-integration address group; scoped bearer-token authentication remains required and is the
primary security boundary.

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
