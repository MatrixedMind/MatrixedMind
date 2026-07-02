# 0007: Use Explicit Sharing, Authorization, and Indexing Policy

## Status

Accepted

## Context

MatrixedMind needs private personal knowledge by default, but it should eventually support public pages, shared spaces, organization/team sharing, and controlled external access.

The app also needs crawler and indexing controls before public pages exist. If public visibility and indexing are bolted on later as template-only flags, authorization behavior will drift across API routes, web routes, exports, backlinks, feeds, and future automation.

## Decision

Model access and indexing policy explicitly in the domain layer and evaluate it through a centralized policy service.

### Principal model

Use these principal types for sharing rules:

- `user`: one authenticated user.
- `organization`: all members of one organization.
- `org_group`: a group inside one organization.
- `external_group`: a controlled outside group.
- `public`: unauthenticated internet access.

`public` must always be explicit. It must never be inferred from missing auth or missing membership.

### Resource scopes

Apply policy at these scopes:

1. Global default.
2. Space policy.
3. Record policy.

Precedence is global default, then space policy, then record policy. More specific rules override less specific rules when they are both applicable.

### Allow and deny behavior

Use deterministic conflict behavior:

- Private by default.
- No indexing by default.
- Explicit deny wins over explicit allow.
- Record-level policy wins over space-level policy when there is no conflict.
- Space-level policy wins over global default when there is no conflict.
- Missing policy means inherit from the next broader scope.

Expose authorization through named checks:

- `can_read`
- `can_edit`
- `can_share`
- `can_discover`

Route handlers, templates, repositories, exports, and future plugins must call this policy boundary instead of reimplementing access checks.

### Indexing and crawler metadata

Support policy fields at global, space, and record scope for:

- `index` / `noindex`
- `follow` / `nofollow`
- `archive` / `noarchive`
- `ai_training` allow/deny
- `automated_browsing` allow/deny

Effective page metadata should be computed from the same policy service that handles visibility and discovery.

### Delayed indexing

When content changes from private to public, do not make it indexable immediately. Add an `index_after` timestamp and default it to a non-zero delay window.

Initial default: **7 days** after the public visibility change.

Owners/admins may override the delay later, but the override must be explicit and audited.

### Audit trail

Record policy changes with:

- actor
- target resource
- previous policy
- new policy
- timestamp
- reason/source when available

## Consequences

### Positive

- Keeps API, web, export, and future plugin access behavior consistent.
- Avoids accidental public or indexable content.
- Gives tests a concrete authorization contract.
- Leaves room for organizations and groups without forcing full multi-tenancy immediately.

### Negative

- More domain model work before polished sharing features exist.
- More tests are required to prevent silent permission regressions.
- The policy service becomes a critical boundary and must stay boring, deterministic, and well-covered.

## Verification expectations

- Tests cover each principal type.
- Tests cover global, space, and record precedence.
- Tests prove deny wins over allow.
- Tests prove list/read results exclude undiscoverable records.
- Tests prove public pages emit crawler metadata from the effective policy.
- Tests prove a private-to-public visibility change is not indexable until `index_after`.
