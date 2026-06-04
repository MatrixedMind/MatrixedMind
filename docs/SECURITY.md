# Security

## Security posture

MatrixedMind is pre-MVP. Security work should focus on clear boundaries, safe defaults, and avoiding shortcuts that would be hard to unwind later.

## Secrets

- Never commit `.env`, `.envrc`, service-account JSON, Application Default Credentials, or generated secret material.
- Use `.env.example` only for names and non-secret defaults.
- Use Secret Manager for cloud secrets.
- Do not reference `latest` Secret Manager versions in production Terraform.
- Do not store secrets in tests or docs.

## Authentication

Local/dev auth and production auth must be separated behind an auth dependency boundary. Development shortcuts must not become production behavior.

Production auth must not rely on a shared secret, hard-coded token, or network obscurity.

## Authorization

Before multi-user features expand, define how users, memberships, spaces, and records relate. Route protection should be tested for both allowed and denied cases.

### Principal and scope matrix

Use explicit principal types for sharing rules:

| Principal type   | Description                             | Notes                                     |
|------------------|-----------------------------------------|-------------------------------------------|
| `user`           | One specific account                    | Most precise grant target.                |
| `organization`   | All members of one organization         | Prefer for broad internal sharing.        |
| `org_group`      | A group inside one organization         | Team-level access within an org boundary. |
| `external_group` | A group outside the owning organization | Use for controlled partner collaboration. |
| `public`         | Unauthenticated internet access         | Should remain explicit, never implied.    |

Apply rules at multiple scopes with deterministic precedence:

| Scope          | Typical owner       | Recommended precedence |
|----------------|---------------------|------------------------|
| Global default | Platform config     | Lowest                 |
| Space policy   | Space owner/admin   | Middle                 |
| Record policy  | Record owner/editor | Highest                |

Policy evaluation should remain centralized in a service boundary and expose reusable checks such as `can_read`, `can_edit`, `can_share`, and `can_discover`.

### Baseline defaults

- Default new spaces and records to private.
- Default crawler/indexing directives to restrictive values until explicitly relaxed.
- Keep "deny" outcomes explicit and testable when allow and deny rules conflict.

## Crawler and indexing controls

MatrixedMind should support crawler/indexing policy at global, space, and record levels with clear inheritance and override behavior.

Recommended metadata controls:

- `index` / `noindex`
- `follow` / `nofollow`
- `archive` / `noarchive`
- `ai_training` allow/deny marker
- `automated_browsing` allow/deny marker

### Delayed indexability safety window

When visibility changes from private to public, apply a default non-zero hold period before content is indexable (`index_after` style behavior). This reduces accidental immediate capture by crawlers and archival bots.

The delay window does not replace proper access control; it is a defense-in-depth mitigation. All visibility and indexing policy changes should produce audit records with the actor, target, previous policy, new policy, and timestamp.

## Data handling

MatrixedMind stores personal knowledge content. Treat record bodies, revisions, metadata, and exports as sensitive user data.

Import/export features must avoid writing outside intended directories and should document the export format clearly.

## Dependencies

Use `uv.lock` for repeatable dependency resolution. Dependency upgrades should run the quality checks in `docs/DEVELOPMENT.md`.

## Infrastructure

Use Workload Identity Federation for GitHub Actions. Do not create or commit service-account keys. Keep IAM scoped to the minimum permissions needed by each deployment component.

## Local development

Core local development must work without GCP credentials. If GCP credentials are needed for a specific task, document why and keep them outside the repository.

## Reporting security issues

Until a formal process exists, document suspected security issues in the project tracker or private notes, then add tests or ADR updates when the behavior is fixed.
