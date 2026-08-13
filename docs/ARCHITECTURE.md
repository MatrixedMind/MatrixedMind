# MatrixedMind Architecture

## Product and deployment shape

MatrixedMind software is a modular monorepo that normally builds one provider-free OCI container.
An **Instance** is a deployment. A **Mind** is one owner's personal body of knowledge in that
Instance, and its **Mind owner** controls it. A **Space** is a collection within a Mind; a **Page**
is user content; **Record** is the internal implementation term. A **Connection** is an external
actor with explicitly granted access.

The default is local-first and self-hostable. Cloud hosting, Firebase, generic OIDC, MCP, and GCP
are optional adapters or dependency groups. No git submodules are used. A module is extracted only
when it needs an independent versioning, deployment, operational, governance, or ownership
lifecycle.

## Implemented now

- One FastAPI modular monolith serves server-rendered HTML and JSON.
- `app/web/` contains browser routes and templates; `app/api/` contains JSON and narrow LLM routes.
- `app/domain/` owns models, validation, policy, and ports; `app/adapters/` owns memory and MongoDB
  persistence implementations.
- Records, revisions, Spaces, users, memberships, personal access tokens, and audit events are
  implemented domain concepts. The server-rendered UI uses Page, Space, Mind, and Instance terms.
- Markdown is rendered and sanitized behind an application-owned boundary. Content defaults to
  private and noindex.
- Built-in local owner authentication uses Argon2id credentials; explicit one-time bootstrap and
  recovery; and MatrixedMind-owned opaque, hashed, rotating browser sessions. Browser writes use
  same-origin and session-bound CSRF checks. `APP_ENV=test` retains only an explicit test seam.
- Hashed, scoped, revocable PATs protect `/api/llm/*` independently of browser sessions.
- Local Docker Compose MongoDB is the ordinary development store. Repository contracts cover the
  in-memory and MongoDB adapters. Compose runs MongoDB as an authenticated single-node replica set
  so local transaction behavior matches the automation-write contract.
- Terraform and Cloud Run deployment support, Firestore Enterprise MongoDB compatibility, and the
  hosted edge topology are implemented optional hosted infrastructure.
- The Custom GPT Action contract at `/openapi-llm.json` and its scoped-token API are implemented
  legacy/provisional capability. They are not the permanent Connection model and are not yet being
  retired.

## Planned architecture

Provider adapters (Firebase and generic OIDC) will establish an external identity, but MatrixedMind
will retain user mapping, authorization, and session control. PATs do not replace the later
Connection and access-grant model.

Later milestones add Connections and grants, authorization-aware retrieval, optional MCP safe
capture, and portable archive import/export. The versioned directory export described by ADR 0009
remains planned. Any replacement for the legacy Custom GPT Action path must preserve or improve
its grants, scopes, revocation, attribution, auditability, and rollback path before retirement.

## Boundaries

- Domain code does not import route modules or provider SDKs.
- Routes use domain services, ports, and auth dependencies rather than database clients.
- Adapters contain provider and storage details; optional dependency groups prevent them becoming
  requirements for a local Instance.
- MatrixedMind, not an identity provider, owns authorization and browser-session policy.
- Infrastructure does not import application code. GCP configuration is not necessary for core
  local behavior.
- Public project documentation is separate from an Instance and its private knowledge.

## Optional hosted path

The hosted GCP path runs the same container on Cloud Run with Artifact Registry, Secret Manager,
and Firestore Enterprise MongoDB compatibility. It may be direct Cloud Run or an external
load-balancer deployment as defined in ADR 0015. Hosted operation must remain compatible with the
portable local baseline; it is an adapter choice, not the product architecture.

Hosted activation of the Milestone 13 image is intentionally blocked until separately reviewed
changes align Terraform's auth mode, add owner-qualified Firestore indexes, map existing `dev-user`
records/PATs to the chosen Mind owner, verify the auth and automation transactions against the
dedicated Firestore compatibility database, establish a canonical trusted HTTPS browser origin,
and provide shared authentication-attempt limiting for multi-instance operation.

## Current route boundary

- Browser pages and the internal record API are protected application surfaces.
- `/api/llm/*` is a narrow, scoped, non-destructive legacy/provisional API for the Custom GPT
  Action. It defaults writes to private, draft, and noindex, creates revisions and audit events,
  and does not expose general administration or destructive operations. Its upsert returns only
  after an application-owned automation-write unit commits the owner-qualified record mutation,
  revision, and required audit event together. The in-memory adapter rolls back both stores on
  failure; MongoDB uses one short session transaction across the existing `records` and
  `audit_events` collections.
- `/openapi-llm.json` publishes only that legacy/provisional Action contract.

## Durable documentation

Keep accepted decisions, user guidance, and contracts in the repository. Use GitHub Issues for
unresolved questions and actionable work. This keeps an Instance deployable and understandable
without depending on an issue tracker, while retaining a practical work queue.
