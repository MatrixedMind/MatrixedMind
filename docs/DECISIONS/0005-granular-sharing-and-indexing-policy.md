# 0005: Granular sharing and indexing policy model

## Status

Accepted

## Context

MatrixedMind needs strong security controls for private knowledge while still supporting intentional sharing. The backlog includes requirements for granular sharing targets (specific users, organizations, internal groups, external groups, and the public), cross-space references, and crawler/indexing controls at multiple levels.

If authorization and indexing behavior are introduced ad hoc in routes and templates, later milestones risk incompatible behavior, metadata leaks, and broad refactors.

## Decision

Adopt a policy-driven model with these boundaries:

1. Model principals explicitly: `user`, `organization`, `org_group`, `external_group`, and `public`.
2. Evaluate access through centralized policy services that expose at least `can_read`, `can_edit`, `can_share`, and `can_discover` checks.
3. Apply deterministic policy precedence across scopes: global defaults, then space-level policy, then record-level policy.
4. Support crawler/indexing controls at global, space, and record levels with documented inheritance and overrides.
5. Apply a default delayed-indexing hold period when content changes from private to public.
6. Emit audit records for sharing and indexing changes.

## Consequences

### Positive

- Security behavior becomes consistent across API routes, web UI, references, exports, and future plugins.
- The principal model can support enterprise-style sharing without redesigning core abstractions.
- Deterministic precedence rules reduce ambiguous access outcomes.
- Delayed indexing adds defense in depth for accidental exposure.
- Audit logs improve incident response and policy debugging.

### Negative

- The policy model adds implementation complexity during Milestones 5 and 6.
- Extra test coverage is required for combinations of principal type, scope, and precedence.
- Delayed indexing introduces operational expectations that must be documented for users.
- Some integrations (search/indexing pipelines, external automation) may need adapters to honor policy metadata.

## Follow-up work

- Finalize policy schema and precedence semantics by the end of Milestone 6.
- Finalize baseline crawler/indexing semantics by the end of Milestone 5.
- Add policy matrix documentation in `docs/SECURITY.md`.
- Add roadmap verification items for share scenarios, precedence behavior, and indexing-delay behavior.
