# MatrixedMind

MatrixedMind is a personal knowledge application built with FastAPI, Markdown-first content, local-first development, and GCP deployment via Terraform.

## Current status

Pre-MVP / active rebuild. The current codebase contains:

- A single FastAPI app in `app/main.py`.
- `/health` and `/ready` endpoints.
- Local MongoDB wiring through Docker Compose.
- Core domain models for records, revisions, spaces, tags, users, and memberships.
- Domain validation rules for slugs, paths, titles, Markdown bodies, and tag values.
- Initial record repository protocol plus memory and MongoDB adapters, with MongoDB covered by the repository contract.
- JSON record routes for `create`, `read`, `update`, and `list`.
- Initial server-rendered home and record detail pages.

The canonical working plan remains [docs/ROADMAP.md](docs/ROADMAP.md). Some code reaches ahead of the current milestone; treat it as provisional until the roadmap verification for that milestone is complete.

The near-term cloud MVP direction is documented in [docs/CLOUD_MVP.md](docs/CLOUD_MVP.md). It targets Cloud Run, Firestore Enterprise MongoDB compatibility pending repository contract verification, and a narrow ChatGPT Custom GPT Action API. No cloud MVP implementation is complete yet.

## Developer quickstart

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Cloud MVP

See [docs/CLOUD_MVP.md](docs/CLOUD_MVP.md).
