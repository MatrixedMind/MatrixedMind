# 0003: Build Server-Rendered UI First

## Status

Accepted

## Context

MatrixedMind needs to become usable as a personal wiki before it needs a complex client-side application. A separate SPA would add build tooling, deployment complexity, API coupling, and design churn before the core workflows are proven.

## Decision

Start with server-rendered HTML from FastAPI. Use templates for the home page, record detail pages, editor pages, and simple navigation. Keep JSON API endpoints available for internal workflows, tests, and future automation.

## Consequences

### Positive

- Faster path to a usable local app.
- Less frontend infrastructure.
- Easier end-to-end testing at the current scale.
- Clearer alignment with the modular monolith.

### Negative

- Rich editor behavior may eventually require targeted client-side code.
- A future SPA or hybrid UI may require route and template refactoring.
- Template discipline matters as pages grow.
