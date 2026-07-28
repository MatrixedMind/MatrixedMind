# 0010: Require CI Quality Gates Before Merge

## Status

Accepted

## Context

MatrixedMind is being built incrementally with AI-assisted development. The repo needs branch protection expectations that prevent agents or humans from stacking unverified changes on `main`.

The roadmap already requires a CI quality gate before later deployment work. This ADR defines what that means.

## Decision

Require pull requests for changes to `main` once the CI workflow exists.

Expected branch protection for `main`:

- Require pull request before merge.
- Require status checks to pass before merge.
- Require the primary CI workflow to pass.
- Require branches to be up to date before merge when practical.
- Block force pushes to `main`.
- Block deletion of `main`.
- Prefer squash merge for normal feature work to keep history readable.
- Allow admins to bypass only for explicit repository recovery or emergency fixes.

The required CI workflow must run at least:

- `uv sync --locked`
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy app`
- `uv run pytest`
- Docker image build

Terraform checks are required when infrastructure files change:

- `terraform fmt -check` or recursive equivalent
- `terraform validate`
- `terraform plan` for the targeted environment when credentials/workspace are available

## Consequences

### Positive

- Keeps `main` trustworthy.
- Makes AI-agent changes reviewable and reversible.
- Prevents merges that break basic local development, tests, typing, or container packaging.
- Creates a clean separation between CI verification and later deployment automation.

### Negative

- Small documentation or typo changes may need a PR once protection is enabled.
- Terraform plan checks require careful credential setup.
- CI may need occasional maintenance as tooling changes.

## Verification expectations

- Opening a PR triggers CI.
- CI fails on lint, format, type, test, or Docker build failure.
- CI passes on a clean branch.
- Branch protection settings are documented after they are applied in GitHub.

## Implementation status

`.github/workflows/ci.yml` implements the required Python, Docker, and credential-free Terraform
checks and exposes their combined result as `CI / Required`. The default pytest lane runs against a
MongoDB 8 service. A separate manual job can execute the existing Firestore compatibility Cloud Run
job through passwordless GitHub Workload Identity Federation.

Repository branch protection still needs to require `CI / Required` after the first successful pull
request run makes that status available in GitHub. Terraform plans remain credentialed, targeted
operations and are not part of the required credential-free pull-request lane.
