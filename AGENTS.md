# Agent Instructions

## Project name

Always refer to the app as MatrixedMind.

## Codex task naming

- When a task's primary work is implementation or verification for a specific GitHub Issue, name the current task:
  `Issue #{number} - {issue title}`
- When a task's primary work is milestone planning, issue decomposition, coordination, integration, verification, or closeout:
  `Milestone {number} - {milestone title}`
  Take the title from the corresponding heading in `docs/ROADMAP.md`, excluding the `Milestone {number}:` prefix.
- For standalone work that is neither an issue implementation nor milestone coordination, use a concise descriptive task title instead, such as `Documentation update - hosted activation decisions`.

## Source of truth

1. `docs/ROADMAP.md` describes product direction, release/milestone scope, and sequencing.
2. **GitHub Milestones** group issues into releasable capabilities.
3. **GitHub Issues** are the normal unit of actionable implementation work.
4. `docs/DECISIONS/` records accepted architecture decisions and long-lived contracts.
5. **Repository documentation** (`docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`, `docs/OPERATIONS.md`) and `AGENTS.md` define general engineering contracts and architecture boundaries.
6. **Implementation-time context:** Issue-specific prepared context, generated or refreshed against a known `main` commit SHA.
7. `README.md` is only a short project index plus accurate current-status summary.

Do not duplicate large amounts of information across these layers.

## Context lifecycle and preparation model

- **Lifecycle:** `context:needed` → context preparation → `context:ready` → implementation.
- If implementation context was prepared against an older repository state and relevant code or contracts have changed materially:
  `context:ready` → `context:stale` → regenerate context → `context:ready`.
- The context-preparation process records the `main` commit SHA against which the context was prepared.
- The GitHub Issue remains the durable task specification; generated context is implementation-time material that may be refreshed when the repository changes.

## Issue granularity and scope boundaries

A normal implementation issue should be small enough that the implementation agent does not need to maintain a complete mental model of the entire milestone.

Prefer issues that:
- have one coherent objective;
- have explicit boundaries (`Scope` and `Out of scope`);
- have independently verifiable acceptance criteria;
- can normally produce one reviewable PR (or only when clearly justified, a very small set of tightly coupled issues);
- minimize cross-cutting changes.

Do not artificially split work when atomic behavior requires multiple files or components to change together.

## Implementation agent discovery and execution

- An implementation agent normally receives:
  - `AGENTS.md`;
  - one assigned GitHub Issue;
  - issue-specific prepared context (`context:ready`).
- Agents should not automatically reread the entire roadmap, every ADR, all project documentation, or the entire repository for every issue.
- Repository discovery must be targeted to the assigned issue:
  1. Known file or exact repository path → read that file directly.
  2. GitHub state → GitHub MCP.
  3. Symbols, code relationships, usages, tests, or IDE intelligence → PyCharm MCP.
  4. Simple text lookup → targeted search.
  5. Broad repository exploration → only when narrower approaches are insufficient.
- Prefer existing prepared context and targeted PyCharm MCP lookups over broad rediscovery.
- If issue context is insufficient, perform or request a targeted lookup before broadening exploration.
- Do not implement neighboring issues merely because related work is discovered.
- Findings outside issue scope should normally be reported and optionally proposed as a separate issue, not implemented opportunistically.

## Required workflow

1. Before starting work for a new pull request, fetch `origin`, switch to `main`, fast-forward it with `git pull --ff-only origin main`, and create a fresh branch from the updated `main`.
2. Inspect the assigned GitHub Issue and verify that context is ready (`context:ready`). If the issue is in `context:needed` or `context:stale`, context must be prepared or refreshed before implementation begins.
3. Identify all issue dependencies, risk labels (`risk:security`, `risk:data`, `risk:cloud`), and confirm any required owner decisions (`owner-decision` or `blocked`) are resolved before starting implementation.
4. Make small, reviewable changes strictly within the issue scope.
5. Add or update tests with implementation changes.
6. Update documentation in the same change when code changes behavior, routes, settings, commands, architecture boundaries, milestone status, or verification expectations.
7. Commit files before running pre-commit/lint checks if operating in an agent environment that requires a committed state.
8. Run the verification commands specified in the issue and required quality gates.
9. Report failures exactly, including IDE, type, lint, test, Docker, and Terraform errors.

## Decision triage

Ask the owner only for choices that materially affect product behavior, human notification
destinations, spending limits, security or IAM boundaries, data safety or recovery, irreversible
actions, or live external mutations. Clearly distinguish an owner decision from an implementation
choice that the agent makes and discloses.

Do not ask the owner to invent Terraform logical names, display names, filenames, service-account
account IDs, temporary resource names, provider-generated IDs, or other routine implementation
identifiers. Choose them from existing MatrixedMind conventions and common sense. Use read-only
discovery before asking for an identifier that can be safely found.

When an input is needed only for a live apply, include a recommended value in the single audited
mutation plan and request approval once. Do not interrupt separately for each routine input.

## Documentation sync

- Keep `docs/ROADMAP.md` aligned with actual milestone status and implemented-but-provisional code.
- Keep `docs/ARCHITECTURE.md` aligned with application boundaries, implemented routes, adapters, and deferred components.
- Keep `docs/DEVELOPMENT.md` aligned with local setup, environment variables, endpoints, and quality commands.
- Keep `docs/TESTING.md` aligned with the actual test layout and verification expectations.
- Keep `docs/OPERATIONS.md` aligned with health checks, deployment assumptions, Terraform roots, and operational commands.
- Keep `README.md` as a short index plus accurate current-status summary.
- If code and docs disagree, either update the docs to match the code or change the code to match the canonical docs before declaring the work complete.

## Milestone discipline

- Do not stack unverified changes across milestones.
- If existing code reaches ahead of the current milestone, harden it only as needed to satisfy the current milestone.
- Do not introduce a separate frontend application unless the roadmap is updated first.
- Do not introduce a second service or queue unless the roadmap and ADRs are updated first.
- Keep persistence behind repository interfaces and adapters.

## Codex workflow routing

- Require `matrixedmind-milestone-coordinator` for milestone planning, issue decomposition,
  dependency management, owner-decision identification, integration, milestone-wide validation, and
  closeout. Individual implementation tasks are delegated to bounded, issue-scoped agents rather
  than retaining long implementation contexts across the entire milestone.
- Require `matrixedmind-cloud-change-control` for Terraform plan or apply review, drift
  reconciliation, IAM or resource mutation, imports or state moves, identity transitions,
  recovery exercises, and secret rotation. Its explicit approval gate applies before any live
  mutation; do not duplicate its procedure here.
- Require `matrixedmind-copilot-review-loop` after an issue or milestone PR is pushed or when
  Copilot review feedback must be addressed.
- Invoke `matrixedmind-improve-process` at coordinator closeout only for a nonempty process-event
  ledger, a recurring review theme, unresolved process debt, or an owner process-improvement
  request. The skill recommends changes and issue candidates but performs no repository or GitHub
  write. GitHub issue creation requires explicit approval unless the owner later grants narrow
  standing authorization.
- After an issue or milestone is complete, validated, and ready for review, publish its intended
  commits, push its branch, and create or convert its PR against the default branch as ready for
  review; verify it is non-draft before the Copilot loop. These publication steps are standing
  authorization for MatrixedMind implementation work; do not merge or perform unrelated
  remote/cloud mutations without their separate authorization.
- Before classifying an external-command failure as authentication or credentials, distinguish
  sandbox or network denial, local credential retrieval, remote authentication, authorization,
  and Git transport. Treat `gh auth status`, `gh api`, `gh repo`, `git fetch`, `git push`, and
  `git ls-remote` as inconclusive without network access. When network or `.git` writes are
  restricted, request the narrow elevation needed for the preflight or publication command.
- Allow at most one unchanged retry of a failed external command; a further retry requires a
  changed hypothesis, credential state, permission level, or execution environment. Never ask
  for reauthentication based only on a restricted-sandbox failure, and never print tokens,
  credential values, or secret contents.
- Begin coordinator work in the project default `read-only` sandbox with untrusted-command
  approvals. Do not delegate from or elevate a broad-access parent turn unless the access is
  explicitly required and approved; parent runtime overrides take precedence over agent defaults.
- Use no more than two concurrent subagents and keep delegation one level deep. Delegate version-sensitive or
  provider-sensitive GCP, Firebase, Google AI, Gemini CLI, Terraform-on-GCP, and Google API
  research to `gcp_docs_researcher`; its Developer Knowledge MCP server is scoped to that agent
  only and requires local `GOOGLE_DEVELOPER_KNOWLEDGE_API_KEY`. Enabling the service and
  provisioning authentication remain manual or explicitly approved cloud actions.
- Do not use Browser, Chrome, Computer Use, or GUI application-control tools unless the user explicitly requests them and a CLI, API, test client, or purpose-built connector cannot perform the task. Put unavoidable browser verification in a fresh, narrowly scoped task.
- Do not poll GitHub, deployments, or other external systems through repeated model turns in a long-running implementation task. Use a bounded wait or a standalone low-cost monitor with a coarse interval, stop condition, and concise output.

## Quality gates

### Run pre-commit (covers formatting, linting, type checks, and infra checks automatically)

```
uv run pre-commit run --all-files
```

Run this before committing and after any significant batch of changes. It covers the path-specific checks below automatically based on which files changed.

### Always run

```
uv run pre-commit run --all-files
```

These hooks always run regardless of what changed:
- `end-of-file-fixer` — ensures files end with a newline.
- `trailing-whitespace` — strips trailing whitespace.
- `check-merge-conflict` — blocks accidental merge conflict markers.

### App changes (`app/` or `tests/`)

Run when any Python source or test file changes:

```
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
```

For day-to-day local verification, `uv run pre-commit run --all-files` already covers `ruff-format` and `ruff-check` in the configured hook order. Run the commands above individually only when you need targeted troubleshooting or direct CI parity checks. `mypy` and `pytest` must still be run manually (or via CI), because they are not both fully covered by pre-commit hooks here.

### Docker / container changes (`Dockerfile`, `compose.yaml`)

```
docker build -t matrixedmind:local .
docker compose up -d
```

### Infrastructure changes (`infra/`)

Run when any `.tf` file changes:

```
terraform fmt -recursive infra/
terraform validate
terraform plan
```

The pre-commit `terraform-fmt` hook runs automatically on `.tf` files. It skips gracefully if `terraform` is not installed, so it will not block commits on machines without Terraform. `terraform validate` and `terraform plan` require an initialized Terraform workspace (`terraform init`) and must be run manually or via CI when infra changes are intended.

### Documentation changes (`docs/`, `*.md`)

```
uv run pre-commit run --all-files
```

Pre-commit will catch trailing whitespace and EOF issues. No additional lint step is required for documentation-only changes.

## Checklist for implementation changes

- When adding or changing validation rules, include tests for valid inputs, invalid inputs, boundary lengths, empty values, malformed values, and security-sensitive edge cases such as traversal-like paths or null bytes where relevant.
- When adding domain models or fields, verify optional/default behavior, avoid mutable defaults, and document whether the model is implemented, provisional, or planned.
- When changing repository behavior, update reusable contract assertions where possible and add explicit tests for missing records, duplicate records, filtering behavior, and update/revision behavior where relevant.
- When changing adapter behavior, verify both the in-memory adapter and MongoDB adapter remain consistent unless the difference is intentional and documented.
- When updating milestone status or documentation, do not mark behavior as complete unless the listed verification has actually passed or the blocker is recorded exactly.
- Keep documentation descriptive, not aspirational: distinguish implemented behavior from planned or provisional behavior.

## Local development

- Use Python 3.12 with `uv`.
- Use Docker Compose for local backing services.
- Use `.env.example` as the template for local configuration.
- Keep the app bootable locally without GCP credentials for core features.

## Secrets

- Never commit `.env`, `.envrc`, service-account JSON, Application Default Credentials, or generated secret material.
- Use GCP Secret Manager for cloud secrets.
- Do not reference `latest` Secret Manager versions in production Terraform.

## Final operating rule

Leave the repository in a valid state: either passing the relevant milestone verification or failing with an exact blocker list and the next best fix path. Silent partial work is unacceptable.
