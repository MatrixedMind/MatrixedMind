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
- A Terraform Cloud Run baseline with reusable modules, passwordless Firestore OIDC wiring, managed runtime-secret references, health probes, and an opt-in GCP compatibility-test job.
- GitHub Actions CI and development-deploy workflows using Workload Identity Federation and immutable Artifact Registry image tags.

The canonical working plan remains [docs/ROADMAP.md](docs/ROADMAP.md). Some code reaches ahead of the current milestone; treat it as provisional until the roadmap verification for that milestone is complete.

The near-term cloud MVP direction is documented in [docs/CLOUD_MVP.md](docs/CLOUD_MVP.md). It targets Cloud Run, the GCP-verified Firestore Enterprise MongoDB-compatible repository path, and a narrow ChatGPT Custom GPT Action API. The Terraform foundation and compatibility-test job were applied and verified in the development GCP project during milestone 7. The private milestone 9 Cloud Run application service, managed secret versions, hosted persistence readiness, and deployment workflow were deployed and verified on 2026-07-28.

## Developer quickstart

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Cloud MVP

See [docs/CLOUD_MVP.md](docs/CLOUD_MVP.md).
