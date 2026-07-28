# MatrixedMind

MatrixedMind is a private home for the things you want to remember: notes, ideas, research,
projects, plans, and the connections between them.

Think of it as a personal wiki that you own. You can write in plain Markdown, organize information
into spaces and pages, and revise it over time. The goal is to make your knowledge easy to browse
and build on without locking it inside a proprietary notes service—or handing an AI unrestricted
access to your life.

## What would I use it for?

You might use MatrixedMind to:

- Keep notes for a long-running project in one connected place.
- Build a personal reference library for topics you care about.
- Capture ideas and rough drafts now, then organize them later.
- Preserve the history of a page as your thinking changes.
- Eventually let ChatGPT file or retrieve specific notes without giving it permission to delete,
  publish, or browse everything.

The guiding idea is that your notes should remain useful to you first. AI can help at carefully
controlled boundaries, but it should not own the data or decide what becomes public.

## What works today?

MatrixedMind is still an early, pre-MVP project, but its core is taking shape. Today it can:

- Create, view, edit, and list Markdown-based records through a basic web interface or JSON API.
- Organize records into spaces, paths, and tags.
- Keep revisions when records change, with additional audit records for AI-assisted writes.
- Keep new content private and hidden from search-engine indexing by default.
- Separate one owner's records from another owner's records.
- Accept narrowly scoped, authenticated AI-assisted reads and writes through a dedicated API.
- Run locally with MongoDB.
- Run as a private Cloud Run service backed by Google Cloud's hosted Firestore database using
  MongoDB compatibility, managed secrets, and automated deployment checks.

The interface is currently functional rather than polished, and production sign-in is not finished.
This is not yet a service intended for general use or sensitive personal data.

## Where is it going?

The roadmap is working toward a secure personal cloud version of MatrixedMind that is genuinely
useful day to day. Planned capabilities include:

- A limited ChatGPT Action that can create, update, and retrieve private draft notes only within
  explicitly allowed spaces.
- Stable links between pages, so reorganizing or renaming a page does not break its connections.
- Backlinks and safer connections across different spaces.
- Granular sharing controls, with public publishing remaining an explicit choice rather than a
  default.
- Portable export as readable Markdown plus JSON metadata, so your knowledge is recoverable and
  not trapped in MatrixedMind.
- Better operational safeguards, backups, monitoring, and eventually a more polished interface.

MatrixedMind is deliberately growing in small, verified steps. Security, ownership, and portability
come before broad AI access or public publishing.

## For developers

MatrixedMind is a Python/FastAPI application with server-rendered pages, a MongoDB-style repository
boundary, Docker-based local development, and Terraform infrastructure for Google Cloud.

- [Developer setup](docs/DEVELOPMENT.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Cloud MVP](docs/CLOUD_MVP.md)
- [ChatGPT Action setup](docs/CHATGPT_ACTION.md)
- [Testing](docs/TESTING.md)

The roadmap is the source of truth for what is implemented, provisional, or still planned.
