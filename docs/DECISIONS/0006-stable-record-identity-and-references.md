# 0006: Use Stable Record Identity Separate from Slugs

## Status

Accepted

## Context

MatrixedMind records currently have a storage `_id`, a `space`, a mutable `slug`, and an optional `parent_id`. That is enough for basic CRUD, but it is not enough for durable wiki references.

Wiki pages need human-readable URLs, but links should not break just because a title, slug, parent, or path changes. Cross-space references also need authorization checks so backlinks and search results do not leak private metadata.

## Decision

Use a stable application-level record identifier that is separate from the display slug and storage-specific `_id`.

The long-term record identity model is:

- `record_id`: immutable application identifier for a record.
- `space_id` or equivalent stable space identifier: immutable application identifier for a space.
- `slug`: mutable human-readable URL segment unique within its routing scope.
- `parent_id`: optional stable `record_id` of the parent record.
- `path`: derived or denormalized display/navigation value, not the canonical identity.

Keep slugs useful for routing and display, but resolve internal references by stable IDs. Page moves and slug changes must preserve references.

For authored wiki links, use a human-friendly syntax first, then normalize links at save time into explicit link records or link metadata keyed by stable IDs.

A reasonable future syntax is:

```md
[[record-slug]]
[[space-slug/record-slug]]
[[record-id:01HV...]]
```

The exact authoring syntax can evolve, but the stored reference target should be a stable ID once resolved.

## Consequences

### Positive

- Page moves and slug changes do not invalidate internal references.
- Backlinks can be queried reliably.
- Cross-space links can run through authorization checks before display.
- Storage adapters do not need to expose database-native IDs as the app contract.

### Negative

- The domain model needs an explicit migration from current `id` semantics to stable app IDs.
- Slug uniqueness and record identity must be tested separately.
- Link parsing and normalization add a service boundary that does not exist yet.

## Verification expectations

- Tests prove slug changes do not change `record_id`.
- Tests prove parent moves do not break references.
- Tests prove backlink/list queries do not expose records the user cannot discover.
- Repository contract tests cover lookup by stable ID and lookup by route slug once implemented.
