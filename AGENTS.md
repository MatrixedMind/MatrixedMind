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
3. Make small, reviewable changes.
4. Add or update tests with implementation changes.
5. Commit files before running pre-commit/lint checks if operating in an agent environment that requires committed state.
6. Run the verification commands listed in the milestone.
7. Report failures exactly, including IDE, type, lint, test, Docker, and Terraform errors.

## Milestone discipline

- Do not stack unverified changes across milestones.
- If existing code reaches ahead of the current milestone, harden it only as needed to satisfy the current milestone.
- Do not introduce a separate frontend application unless the roadmap is updated first.
- Do not introduce a second service or queue unless the roadmap and ADRs are updated first.
- Keep persistence behind repository interfaces and adapters.

## Quality gates

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy app`
- `uv run pytest`
- `docker build -t matrixedmind:local .` where relevant
- `terraform fmt -check`, `terraform validate`, and `terraform plan` for infrastructure changes

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
