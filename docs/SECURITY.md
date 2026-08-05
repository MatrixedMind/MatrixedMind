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

The public `/source` route contains only the AGPL license notice and corresponding-source link. It
uses restrictive crawler metadata and does not expose record data or a privileged application
capability.

Cloud Run may allow public unauthenticated invocation at the platform layer only when MatrixedMind enforces app-level authentication and authorization for all sensitive routes. Public platform reachability is acceptable for the MVP only because ChatGPT Custom GPT Actions need an HTTPS endpoint they can call.

## LLM API tokens

The LLM API must use tokens that are separate from browser owner authentication and separate from the normal/internal API.

LLM API tokens must be:

- Scoped to allowed operations.
- Scoped to allowed spaces.
- Revocable.
- Hashed at rest.
- Attributed to a known integration and synthetic actor, such as `llm:chatgpt`.
- Protected by rate limits.
- Protected by body size limits.

Do not store plaintext LLM tokens in GitHub, docs, Terraform variables, `.env.example`, logs, or Codex output.

The LLM-facing API must be separate from the internal/general API. Do not expose full record CRUD to ChatGPT.

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
- Default LLM-created records to private, draft, and noindex.
- Restrict initial LLM writes to an allowed space such as `llm-inbox`.

## LLM threat model

The first LLM integration should assume these threats:

- Prompt injection: record content or user instructions may try to make ChatGPT misuse tools.
- Overbroad tools: a schema that exposes normal CRUD or admin endpoints can turn a narrow assistant into a broad actor.
- Leaked token: an API key can be copied from the Custom GPT configuration, logs, or an intermediate system.
- Accidental destructive writes: the model may call an available destructive operation even when the user did not intend it.
- Accidental high-sensitivity content capture: personal or sensitive material may be sent to the LLM API before cloud persistence, auth, backup, audit, and token revocation are ready.

Required controls:

- Keep LLM tools narrow and non-destructive.
- Require scoped tokens.
- Store token hashes only.
- Support token revocation.
- Enforce allowed spaces.
- Reject delete, publish, visibility changes, indexing changes, sharing changes, auth changes, admin actions, and bulk import.
- Create an audit trail for every LLM write.
- Create a revision for every LLM write.
- Default LLM writes to private, draft, and noindex.
- Enforce rate limits.
- Enforce body size limits.

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

Do not store high-sensitivity data until cloud persistence, app-level auth, backup and restore,
audit logging, token revocation, and Firestore Enterprise MongoDB compatibility are implemented and
verified. The remaining non-production rotation and isolated restore exercises are tracked in the
[Cloud MVP verification follow-up register](CLOUD_MVP_VERIFICATION_FOLLOW_UP.md). Until those
requirements are complete, treat hosted data as provisional and suitable only for low-sensitivity
testing.

## External Markdown images

Rendered images require absolute HTTPS URLs. URL credentials, non-default ports, relative sources,
and non-HTTPS schemes are rejected. Sanitization removes event handlers, inline styles, and all
image attributes except `src`, `alt`, and `title`; raw HTML is subject to the same source policy as
Markdown image syntax.

Deployments can leave the image-source allowlist empty or restrict it to exact hosts and explicit
subdomain wildcards. The allowlist is a rendering control, not an upload mechanism, proxy, or
server-side fetch. A viewer's browser still contacts an approved external host, which can observe
the request and can make the image unavailable independently of MatrixedMind.

## Dependencies

Use `uv.lock` for repeatable dependency resolution. Dependency upgrades should run the quality checks in `docs/DEVELOPMENT.md`.

## Infrastructure

Use Workload Identity Federation for GitHub Actions. Do not create or commit service-account keys. Keep IAM scoped to the minimum permissions needed by each deployment component.

## Local development

Core local development must work without GCP credentials. If GCP credentials are needed for a specific task, document why and keep them outside the repository.

## Reporting security issues

Until a formal process exists, document suspected security issues in the project tracker or private notes, then add tests or ADR updates when the behavior is fixed.
