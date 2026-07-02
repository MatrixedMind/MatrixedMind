# Roadmap Decisions

This file summarizes the current roadmap decisions without changing milestone implementation status. Use the ADRs as the source of truth when updating milestone checkboxes.

## Resolved decisions

| Roadmap area | Decision | ADR |
|---|---|---|
| Candidate B / Milestone 5 Markdown rendering | Use `markdown-it-py` for rendering and `nh3` for sanitization behind an application-owned rendering boundary. | `docs/DECISIONS/0013-markdown-rendering-and-sanitization.md` |
| Candidate D stable references | Add a stable application-level `record_id` separate from mutable slugs and storage-native IDs. Resolve internal links to stable IDs. | `docs/DECISIONS/0006-stable-record-identity-and-references.md` |
| Candidate A/E / Milestone 5 crawler policy / Milestone 6 sharing policy | Use explicit principal types, centralized policy checks, global → space → record precedence, private/noindex defaults, deny-wins conflict behavior, and 7-day delayed indexing for private-to-public changes. | `docs/DECISIONS/0007-sharing-authorization-and-indexing-policy.md` |
| Milestone 6 production auth requirements | Separate `dev`, `test`, and `production` auth modes. Production must fail closed when auth is not configured. | `docs/DECISIONS/0008-auth-modes-and-production-requirements.md` |
| Milestone 7 export format | Export Markdown bodies plus JSON metadata in a versioned directory format rooted at `matrixedmind-export/`. Import idempotently by stable IDs. | `docs/DECISIONS/0009-export-directory-format.md` |
| Milestone 8 branch protection | Require PR-based CI checks before merge once the workflow exists. CI must cover uv sync, Ruff, mypy, pytest, and Docker build. | `docs/DECISIONS/0010-ci-quality-gate-and-branch-protection.md` |
| Milestone 9 Terraform roots | Use `infra/terraform/bootstrap`, `infra/terraform/modules`, and `infra/terraform/envs/{dev,prod}`. | `docs/DECISIONS/0011-infrastructure-layout.md` |
| Milestone 10 dev hosting | Keep hosted development access restricted by default. | `docs/DECISIONS/0012-dev-hosting-exposure.md` |

## Roadmap checkbox updates

When updating `docs/ROADMAP.md`, these human decision tasks can be marked complete because they now have ADR-backed answers:

- Milestone 5: finalize robots/indexing metadata model with precedence rules.
- Milestone 5: add delayed-indexing defaults for newly public content and document override behavior.
- Milestone 6: finalize principal model for sharing.
- Milestone 6: finalize authorization policy contract with documented allow/deny precedence.
- Milestone 6: document production auth requirements before selecting a provider.
- Milestone 7: define an export directory format.
- Milestone 8: document required branch protection expectations.
- Milestone 9: define Terraform roots in `infra/terraform/envs/{dev,prod}`.
- Milestone 10: document whether the dev service is public or private.

Do not mark implementation tasks complete until the corresponding code, tests, and verification commands are actually done.
