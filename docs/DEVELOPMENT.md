# Development

## Required tools

- Python 3.12
- `uv`
- Docker Desktop
- Terraform
- Google Cloud CLI
- PyCharm Pro

## Setup

```bash
uv sync --locked
docker compose up -d
uv run pytest
```

Use `.env.example` as the template for local environment variables. Do not commit `.env` or local credential files.

## Environment variables

Required local values:

```text
APP_ENV=local
MONGO_URI=mongodb://matrixed_mind:matrixed_mind@localhost:27017/matrixed_mind?authSource=admin
```

When running through Docker Compose, the `api` service uses the same database credentials with the Compose service host:

```text
MONGO_URI=mongodb://matrixed_mind:matrixed_mind@mongo:27017/matrixed_mind?authSource=admin
```

## Local app

Run the app directly:

```bash
uv run uvicorn app.main:app --reload
```

Run the app and backing services through Docker Compose:

```bash
docker compose up --build
```

The default local app URL is:

```text
http://localhost:8000
```

The health endpoint is:

```text
http://localhost:8000/health
```

The readiness endpoint verifies MongoDB connectivity:

```text
http://localhost:8000/ready
```

## Quality checks

Run these before considering a milestone complete:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
docker build -t matrixedmind:local .
```

For infrastructure changes, also run the checks from `docs/OPERATIONS.md`.

## Common commands

Run a specific test file:

```bash
uv run pytest tests/unit/test_health.py
```

Format Python files:

```bash
uv run ruff format .
```

Start only local backing services:

```bash
docker compose up -d mongo
```

Stop local containers:

```bash
docker compose down
```

## PyCharm

Use the local `uv` interpreter as the primary interpreter. Use the Docker Compose interpreter only when debugging container parity. Keep inspections and commit hooks enabled.

## Development rules

- Read `docs/ROADMAP.md` before adding features.
- Build the current milestone before expanding later milestones.
- Add or update tests with implementation changes.
- Keep persistence behind repository interfaces and adapters.
- Keep the server-rendered UI first unless the roadmap changes.
