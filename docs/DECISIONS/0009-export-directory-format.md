# 0009: Export Records as Markdown Plus JSON Metadata

## Status

Accepted

## Context

MatrixedMind should not trap content inside one database. The storage strategy intentionally starts with MongoDB but keeps other adapters possible. Import/export is the escape hatch that makes the app recoverable, inspectable, and portable.

The export format needs to preserve Markdown bodies, metadata, hierarchy, revisions, and enough identity information to re-import idempotently.

## Decision

Use a directory-based export format with human-readable Markdown bodies and machine-readable JSON metadata.

Initial format:

```text
matrixedmind-export/
  manifest.json
  spaces/
    <space_slug>/
      space.json
      records/
        <record_id>/
          record.json
          body.md
          revisions/
            <revision_id>.json
            <revision_id>.md
```

### `manifest.json`

Contains export-level metadata:

- format name: `matrixedmind-export`
- format version, starting at `1`
- export timestamp
- app version or commit when available
- source adapter name when available

### `space.json`

Contains stable space metadata, not record bodies.

### `record.json`

Contains record metadata:

- `record_id`
- `space_id` or space slug until stable space IDs exist
- `parent_id`
- `slug`
- `path` if stored
- `title`
- `tags`
- `created_at`
- `updated_at`
- policy/indexing metadata when implemented
- revision metadata references

### `body.md`

Contains only the current Markdown body.

### `revisions/`

Each revision stores metadata in JSON and body content in Markdown. Revisions should be imported in timestamp order when reconstructing history.

### Import behavior

Import must be idempotent by stable IDs. If a record already exists with the same `record_id`, update it only when the imported record is newer or when an explicit replace mode is provided. Slug conflicts must fail loudly unless a documented conflict strategy is selected.

Import and export must reject paths that escape the export root.

## Consequences

### Positive

- Markdown content remains easy to inspect, diff, and recover.
- JSON metadata keeps imports deterministic.
- Stable IDs make exports portable across storage adapters.
- The format can be versioned without coupling it to MongoDB document shape.

### Negative

- Export/import code must handle metadata/body consistency.
- Revision-heavy content can produce many small files.
- Conflict handling needs explicit tests before imports are trusted.

## Verification expectations

- Tests export fixture records and revisions into the expected directory shape.
- Tests delete/recreate a local database and import the export.
- Tests confirm current bodies, metadata, hierarchy, and revisions match.
- Tests reject path traversal and malformed manifests.
- Tests prove repeated import is idempotent.
