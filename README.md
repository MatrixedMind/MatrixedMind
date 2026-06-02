# MatrixedMind

MatrixedMind is a personal knowledge/wiki application built with FastAPI, Markdown-first content, local-first development, and GCP deployment via Terraform.

## Current status

Pre-MVP / active rebuild. The current codebase contains:

- A single FastAPI app in `app/main.py`.
- `/health` and `/ready` endpoints.
- Local MongoDB wiring through Docker Compose.
- Initial `Record` and `RecordRevision` domain models.
- Initial record repository protocol plus memory and MongoDB adapters.
- Initial JSON record routes for `create`, `read`, and `list`.
- Initial server-rendered home and record detail pages.

The canonical working plan remains [docs/ROADMAP.md](docs/ROADMAP.md). Some code reaches ahead of the current milestone; treat it as provisional until the roadmap verification for that milestone is complete.

## Developer quickstart

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
