# 0002: Use Repository Interfaces and Storage Adapters

## Status

Accepted

## Context

MatrixedMind needs local-first development with MongoDB now, while keeping the option to use Firestore, Firestore Mongo compatibility, or another storage backend later. Route and domain code should not be rewritten for every storage decision.

## Decision

Keep persistence behind repository interfaces. Start with a MongoDB adapter for local development and early deployment. Application code should depend on repository protocols and dependency providers rather than concrete database clients.

## Consequences

### Positive

- Storage choices remain reversible longer.
- Repository contract tests can verify adapters consistently.
- Local MongoDB development can move quickly.
- Cloud storage changes can be isolated later.

### Negative

- Interfaces must be designed carefully enough to stay useful.
- Adapter tests add work.
- Some database-specific capabilities may be intentionally deferred.
