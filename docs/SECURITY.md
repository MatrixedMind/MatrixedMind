# Security

## Security posture

MatrixedMind is pre-MVP. Security work should focus on clear boundaries, safe defaults, and avoiding shortcuts that would be hard to unwind later.

## Secrets

- Never commit `.env`, `.envrc`, service-account JSON, Application Default Credentials, or generated secret material.
- Use `.env.example` only for names and non-secret defaults.
- Use Secret Manager for cloud secrets.
- Do not reference `latest` Secret Manager versions in production Terraform.
- Do not store secrets in tests or docs.

## Authentication

Local/dev auth and production auth must be separated behind an auth dependency boundary. Development shortcuts must not become production behavior.

Production auth must not rely on a shared secret, hard-coded token, or network obscurity.

## Authorization

Before multi-user features expand, define how users, memberships, spaces, and records relate. Route protection should be tested for both allowed and denied cases.

## Data handling

MatrixedMind stores personal knowledge content. Treat record bodies, revisions, metadata, and exports as sensitive user data.

Import/export features must avoid writing outside intended directories and should document the export format clearly.

## Dependencies

Use `uv.lock` for repeatable dependency resolution. Dependency upgrades should run the quality checks in `docs/DEVELOPMENT.md`.

## Infrastructure

Use Workload Identity Federation for GitHub Actions. Do not create or commit service-account keys. Keep IAM scoped to the minimum permissions needed by each deployment component.

## Local development

Core local development must work without GCP credentials. If GCP credentials are needed for a specific task, document why and keep them outside the repository.

## Reporting security issues

Until a formal process exists, document suspected security issues in the project tracker or private notes, then add tests or ADR updates when the behavior is fixed.
