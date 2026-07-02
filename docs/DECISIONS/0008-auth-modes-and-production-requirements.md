# 0008: Separate Dev Auth from Production Auth Requirements

## Status

Accepted

## Context

MatrixedMind needs a fast local development loop now and real authentication later. A local shortcut is acceptable only if it is impossible to confuse with production behavior.

The previous proof-of-concept used a shared-secret style shortcut. That pattern must not become the production model for a browser-facing wiki.

## Decision

Use explicit auth modes behind a stable auth dependency boundary.

### Auth modes

Support these application modes:

- `dev`: local-only fake authenticated user for development and tests.
- `test`: deterministic test identities controlled by tests.
- `production`: real externally verified identity, no fake user fallback.

Production startup must fail closed if auth is not configured.

### Production auth requirements

Before selecting or implementing a hosted provider, production auth must satisfy these requirements:

- No shared-secret header as the user identity mechanism.
- No hard-coded demo user.
- No password storage in MatrixedMind for the first production version.
- Verified identity from a managed provider or trusted upstream proxy.
- Server-side session or verified token handling with clear expiration.
- CSRF protection for browser form writes.
- Secure cookie settings for hosted browser sessions.
- User identity mapped to MatrixedMind `User` records by stable provider subject, not mutable email alone.
- Logout behavior documented and tested.
- Authorization remains app-owned; identity provider groups may be inputs, not the only policy source.

The likely GCP-native production provider remains Identity Platform, but this ADR intentionally records requirements rather than final provider selection.

## Consequences

### Positive

- Keeps local development easy without weakening production boundaries.
- Lets Milestone 6 build route protection before final provider integration.
- Avoids carrying forward the proof-of-concept shared-secret shortcut.
- Makes provider selection easier because requirements are explicit.

### Negative

- The first production auth implementation still needs a separate provider-selection decision.
- Browser sessions add security details that API-only auth would avoid.
- Tests must prove dev/test auth cannot activate in production mode.

## Verification expectations

- Tests prove `dev` mode returns a deterministic development user.
- Tests prove protected routes reject unauthenticated requests when not in dev/test mode.
- Tests prove production mode fails closed when required auth settings are missing.
- Tests prove record creation and revisions receive user context from the auth dependency.
