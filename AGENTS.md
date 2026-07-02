# Agent Instructions

## Project name

Always refer to the app as MatrixedMind.

## Source of truth

- `docs/ROADMAP.md` is the canonical working plan until the app is real.
- `README.md` is only a short project index for now.
- `docs/ARCHITECTURE.md` explains the intended system shape.
- `docs/DEVELOPMENT.md` contains local setup and quality commands.
- `docs/TESTING.md` defines what verification means.
- `docs/DECISIONS/` records accepted architecture decisions.

## Required workflow

1. Read `docs/ROADMAP.md`.
2. Work only on the current milestone unless instructed otherwise.
3. Identify all milestone tasks marked as human intervention or decision tasks and confirm they are resolved (or explicitly blocked) before starting AI-agent implementation tasks.
4. Make small, reviewable changes.
5. Add or update tests with implementation changes.
6. Update documentation in the same change when code changes behavior, routes, settings, commands, architecture boundaries, milestone status, or verification expectations.
7. Commit files before running pre-commit/lint checks if operating in an agent environment that requires a committed state.
8. Run the verification commands listed in the milestone.
9. Report failures exactly, including IDE, type, lint, test, Docker, and Terraform errors.

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
