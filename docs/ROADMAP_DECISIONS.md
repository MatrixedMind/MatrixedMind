# Roadmap Decisions

This file summarizes the current roadmap decisions without changing milestone implementation status. Use the ADRs as the source of truth when updating milestone checkboxes.

## Resolved decisions

| Roadmap area | Decision | ADR |
|---|---|---|
| Candidate B / Milestone 5 Markdown rendering | Use `markdown-it-py` for rendering and `nh3` for sanitization behind an application-owned rendering boundary. | `docs/DECISIONS/0013-markdown-rendering-and-sanitization.md` |
| Candidate D stable references | Add a stable application-level `record_id` separate from mutable slugs and storage-native IDs. Resolve internal links to stable IDs. | `docs/DECISIONS/0006-stable-record-identity-and-references.md` |
| Candidate A/E / Milestone 5 crawler policy / Milestone 6 sharing policy | Use explicit principal types, centralized policy checks, global → space → record precedence, private/noindex defaults, deny-wins conflict behavior, and 7-day delayed indexing for private-to-public changes. | `docs/DECISIONS/0007-sharing-authorization-and-indexing-policy.md` |
| Milestone 6 production auth requirements | Separate `dev`, `test`, and `production` auth modes. Production must fail closed when auth is not configured. | `docs/DECISIONS/0008-auth-modes-and-production-requirements.md` |
| Deferred import/export format | Export Markdown bodies plus JSON metadata in a versioned directory format rooted at `matrixedmind-export/`. Import idempotently by stable IDs. | `docs/DECISIONS/0009-export-directory-format.md` |
| Milestone 8 branch protection | Require PR-based CI checks before merge once the workflow exists. CI must cover uv sync, Ruff, mypy, pytest, and Docker build. | `docs/DECISIONS/0010-ci-quality-gate-and-branch-protection.md` |
| Milestone 9 Terraform roots | Use `infra/terraform/bootstrap`, `infra/terraform/modules`, and `infra/terraform/envs/{dev,prod}`. | `docs/DECISIONS/0011-infrastructure-layout.md` |
| Hosted development exposure | Keep hosted development access restricted by default; any public platform reachability must be paired with app-level auth. | `docs/DECISIONS/0012-dev-hosting-exposure.md` |
| Cloud MVP direction | Use Cloud Run as the HTTPS host for the first secure cloud MVP, with public platform invocation allowed only after app-level auth protects sensitive routes. | `docs/DECISIONS/0014-cloud-mvp-firestore-mongo-and-chatgpt-action.md` |
| Cloud persistence | Prefer Firestore Enterprise edition with MongoDB compatibility for cloud persistence, prove compatibility with repository contract tests before deployment is unblocked, and keep MongoDB Atlas as fallback only. | `docs/DECISIONS/0014-cloud-mvp-firestore-mongo-and-chatgpt-action.md` |
| First ChatGPT integration | Use Custom GPT Actions with API key authentication as the first LLM integration path. Defer OAuth and MCP. | `docs/DECISIONS/0014-cloud-mvp-firestore-mongo-and-chatgpt-action.md` |
| LLM write API | Expose a separate narrow, scoped, non-destructive `/api/llm/*` API. LLM tokens must be scoped, revocable, hashed at rest, and constrained to allowed spaces and operations. | `docs/DECISIONS/0014-cloud-mvp-firestore-mongo-and-chatgpt-action.md` |
| Milestone 11 deployment topology | Reuse an existing shared external HTTPS load balancer and static IP for the hosted deployment. Self-hosters choose exactly one Terraform mode: direct public Cloud Run or external-load-balancer routing with direct ingress blocked. | `docs/DECISIONS/0015-hosted-and-self-hosted-deployment-modes.md` |
| Milestone 13 official documentation mirror | Keep the official mirror opt-in and separate from self-hosted defaults. Start with manual, reviewed publishing from a deliberately configured source, and translate supported repository-relative links deterministically. | `docs/DECISIONS/0016-official-public-documentation-mirror.md` |
| Milestone 11 external Markdown images | Allow safe external HTTPS images with optional configured source allowlists, preserving only required attributes. Defer uploads and portable storage-backed attachments. | `docs/DECISIONS/0017-external-markdown-image-policy.md` |

## Roadmap checkbox updates

When updating `docs/ROADMAP.md`, these human decision tasks can be marked complete because they now have ADR-backed answers:

- Milestone 5: finalize robots/indexing metadata model with precedence rules.
- Milestone 5: add delayed-indexing defaults for newly public content and document override behavior.
- Milestone 6: finalize principal model for sharing.
- Milestone 6: finalize authorization policy contract with documented allow/deny precedence.
- Milestone 6: document production auth requirements before selecting a provider.
- Later import/export work: define an export directory format.
- Milestone 8: document required branch protection expectations.
- Milestone 9: define Terraform roots in `infra/terraform/envs/{dev,prod}`.
- Hosted development exposure: document whether the dev service is public or private.
- Milestone 6-11 cloud MVP direction: Cloud Run, Firestore Enterprise MongoDB compatibility with MongoDB Atlas fallback only, API-key-authenticated Custom GPT Actions, and a narrow non-destructive LLM write API.
- Milestone 11 deployment mode: use the existing shared external load balancer for the hosted
  deployment while keeping direct public Cloud Run as a mutually exclusive self-hosted mode.

Do not mark implementation tasks complete until the corresponding code, tests, and verification commands are actually done.
