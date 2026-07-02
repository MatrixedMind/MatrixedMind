# 0001: Use FastAPI Modular Monolith

## Status

Accepted

## Context

MatrixedMind needs to be easy to run locally, deployable to Cloud Run, and simple enough to build iteratively. The app needs both browser-facing pages and JSON endpoints, but it does not yet need separate services or a separate frontend application.

## Decision

Use one FastAPI application serving both HTML and JSON. Organize the code as a modular monolith with clear internal boundaries for web routes, API routes, domain models, repository interfaces, adapters, auth, and infrastructure.

## Consequences

### Positive

- Simple deployment.
- Python-first codebase.
- Easier local development.
- Easier testing.
- Better fit for Cloud Run.
- Less coordination overhead while the product shape is still changing.

### Negative

- UI complexity must be kept under control.
- Future API/frontend separation may require refactoring.
- Internal boundaries must be maintained by convention and tests.
