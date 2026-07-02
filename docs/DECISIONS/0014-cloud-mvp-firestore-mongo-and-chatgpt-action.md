# 0014: Cloud MVP with Firestore Mongo Compatibility and ChatGPT Action

## Status

Accepted

## Context

MatrixedMind needs a secure cloud MVP that is reachable over HTTPS and usable from ChatGPT through a narrow write API. The current app is a Python-first FastAPI modular monolith with MongoDB-style repository adapters, repository contract tests, and Docker Compose MongoDB for local development.

The MVP must stay private by default. ChatGPT needs a reachable HTTPS endpoint, but that does not mean MatrixedMind should expose broad unauthenticated app behavior.

## Decision

Use Cloud Run for the first cloud MVP.

Use Firestore Enterprise edition with MongoDB compatibility as the preferred cloud persistence target. This choice is conditional: Firestore compatibility must be proven by repository contract tests before cloud deployment is considered unblocked.

Keep existing local Docker Compose MongoDB as the local development path.

Keep MongoDB Atlas as the fallback only if Firestore MongoDB compatibility fails or blocks the MVP.

Use Custom GPT Actions with API key authentication as the first ChatGPT integration path. Do not use OAuth or MCP for the first MVP.

Cloud Run may allow unauthenticated invocation at the platform layer so ChatGPT can reach the service, but MatrixedMind must enforce app-level authentication and authorization for all sensitive routes.

Keep the LLM-facing API separate from the internal/general API.

LLM tokens must be scoped, revocable, hashed at rest, and limited to allowed spaces and allowed operations.

LLM writes must default to private, draft, and noindex.

LLM writes must create append-only revisions and audit events.

Destructive actions are out of scope for the LLM MVP. The LLM must not delete records, publish records, change visibility, change indexing policy, change sharing policy, change authentication settings, run admin actions, or bulk import data.

Defer MCP, OAuth, multi-user sharing, import/export, custom domain, and public publishing until after the secure cloud MVP path is working.

## Consequences

### Positive

- Gives MatrixedMind a short path to a usable private cloud MVP.
- Reuses the current MongoDB adapter direction if Firestore compatibility is sufficient.
- Keeps local development simple and independent of GCP credentials.
- Makes the ChatGPT integration narrow and reviewable.
- Preserves private-by-default behavior while still allowing ChatGPT to call a public HTTPS URL.

### Negative

- Firestore MongoDB compatibility may not match local MongoDB behavior closely enough.
- Repository contract tests need to run against another real backing service.
- Public Cloud Run invocation increases the importance of app-level auth, rate limits, body limits, and audit logging.
- Append-only revisions and audit events add implementation work before the cloud path should be trusted with sensitive data.

## Verification expectations

- Repository contract tests pass against local Docker Compose MongoDB.
- Repository contract tests pass against Firestore Enterprise MongoDB compatibility before cloud deployment is unblocked.
- Tests verify unique index behavior, `ObjectId` handling, duplicate-key behavior, `update_one` with `$set`, sorting, and readiness checks against Firestore compatibility.
- Browser routes require owner auth before public Cloud Run invocation is allowed.
- `/api/llm/*` requires scoped LLM tokens.
- LLM tests prove allowed create/update/read behavior inside allowed spaces.
- LLM tests prove delete, publish, visibility changes, indexing changes, sharing changes, auth changes, admin actions, bulk import, and writes outside allowed spaces are forbidden.
- Every LLM write creates a revision and an audit event.
- Token revocation is tested.

## Deferred

- OAuth.
- MCP.
- ChatGPT Apps SDK.
- Multi-user sharing UI.
- Import/export implementation.
- Public publishing.
- Custom domain.
- Polished browser UI.
