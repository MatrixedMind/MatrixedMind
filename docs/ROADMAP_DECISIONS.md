# Roadmap Decisions

This is a concise index of accepted decisions that shape the active roadmap. ADRs remain the
source of truth. Unresolved decisions and actionable implementation work belong in GitHub Issues;
durable user guidance, contracts, and accepted decisions stay in this repository.

| Area | Accepted direction | ADR |
|---|---|---|
| Product vocabulary | MatrixedMind software runs as an Instance; a Mind is one owner's personal body of knowledge, Spaces contain Pages, Connections are external actors, and Record is internal terminology. | `0018`, `0019` |
| Owner authentication | Built-in local Argon2id credentials and MatrixedMind-owned rotating sessions are the portable baseline; provider identity is optional. Initial session defaults are 30 days inactive, 90 days absolute, and eight-hour rotation without interactive login. | `0018` |
| Identity adapters | Firebase, generic OIDC, hosted/GCP, and MCP capabilities are optional adapters/dependency groups. | `0018`, `0019` |
| Repository shape | Keep one modular monorepo and one default OCI-container deployment. Do not use git submodules; extract only for an independent lifecycle. | `0001`, `0019` |
| Authorization and indexing | Use centralized policy checks, explicit principals, deterministic inheritance, deny-wins behavior, and private/noindex defaults. | `0007` |
| Export/import | Use a versioned directory export rooted at `matrixedmind-export/`, with Markdown bodies and JSON metadata, then import idempotently by stable IDs. | `0009` |
| Cloud MVP | Cloud Run and Firestore MongoDB compatibility remain an optional hosted path, behind app-level security. | `0014`, `0015` |
| Legacy ChatGPT path | The implemented Custom GPT Action with scoped bearer tokens is legacy/provisional. Keep it until a verified replacement exists; retirement is not yet scheduled. | `0014`, `0018` |
| Personal access tokens | Generalize the existing credential primitive into provider-neutral PATs for scripts and legacy clients, with explicit attribution, scopes, hashed storage, and revocation. PATs are not Connection grants. | `0018` |
| Public project docs | Public docs are opt-in, reviewed, and separate from private Instance content. | `0016`, `0017`, `0019` |

ADR 0018 supersedes the provider-only and no-local-password portions of ADR 0008. ADR 0008 remains
historical evidence for dev/test separation and fail-closed route protection.
