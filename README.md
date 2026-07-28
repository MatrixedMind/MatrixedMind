# MatrixedMind

MatrixedMind is a personal knowledge application built with FastAPI, Markdown-first content, local-first development, and GCP deployment via Terraform.

## Current status

Pre-MVP / active rebuild. The current codebase contains:

- A single FastAPI app in `app/main.py`.
- `/health` and `/ready` endpoints.
- Local MongoDB wiring through Docker Compose.
- Core domain models for records, revisions, spaces, tags, users, and memberships.
- Domain validation rules for slugs, paths, titles, Markdown bodies, and tag values.
- Provisional crawler/indexing policy helpers with private/noindex defaults and delayed indexing for public records.
- Initial record repository protocol plus memory and MongoDB adapters, with MongoDB covered by the repository contract.
- JSON record routes for `create`, `read`, `update`, and `list`.
- Server-rendered home, record detail, and record editor pages with basic form handling.
- A Terraform Cloud MVP foundation with passwordless Firestore OIDC wiring, managed indexes, and an opt-in GCP compatibility-test job.
- A GitHub Actions CI quality gate for locked dependencies, Ruff, mypy, tests against local MongoDB, Docker builds, Terraform static validation, and optional passwordless Firestore compatibility runs.

The canonical working plan remains [docs/ROADMAP.md](docs/ROADMAP.md). Some code reaches ahead of the current milestone; treat it as provisional until the roadmap verification for that milestone is complete.

The near-term cloud MVP direction is documented in [docs/CLOUD_MVP.md](docs/CLOUD_MVP.md). It targets Cloud Run, the GCP-verified Firestore Enterprise MongoDB-compatible repository path, and a narrow ChatGPT Custom GPT Action API. The Terraform foundation and compatibility-test job have been applied and verified in the development GCP project; the application service remains disabled until its deployment milestone.

## Developer quickstart

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Cloud MVP

See [docs/CLOUD_MVP.md](docs/CLOUD_MVP.md).
