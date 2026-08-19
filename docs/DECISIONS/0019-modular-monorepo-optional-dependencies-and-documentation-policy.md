# 0019: Modular Monorepo, Optional Dependencies, and Documentation Policy

## Status

Accepted

## Context

MatrixedMind needs to remain inspectable, portable, and straightforward to operate while it gains
hosted integrations and external Connections. Splitting repositories, adding submodules, or making
cloud dependencies mandatory would make a self-hosted Instance harder to own and recover.

## Decision

Keep MatrixedMind as one modular monorepo and one default deployable OCI container. Maintain clear
internal boundaries for domain logic, web/API routes, persistence, authentication, and optional
adapters. Do not use git submodules.

Firebase, generic OIDC, MCP, hosted/GCP, and other provider integrations are optional adapters and
dependency groups. A local Instance must not require their packages, credentials, or configuration
for core owner and Page behavior.

Extract a package, service, or repository only when it has a demonstrated independent lifecycle:
separate versioning, deployment, scaling, operational ownership, governance, or release cadence.
Organizational preference alone is insufficient.

Keep durable user guidance, contracts, architecture, and accepted decisions in the repository.
Use GitHub Issues for unresolved decisions and actionable work. Public project documentation is
separate from private Instance knowledge and remains opt-in.

## Consequences

### Positive

- A Mind owner can run, inspect, export, and transfer the software without a provider account.
- Optional integrations do not define the core installation or data model.
- The repository remains the durable source for behavior and decisions.

### Negative

- Internal module boundaries need discipline and tests as the codebase grows.
- Optional dependency groups and adapter contracts require compatibility coverage.
- A later extraction requires evidence and a deliberate migration plan.

## Verification expectations

- Build and test a core local container/install without optional provider dependency groups.
- Test optional adapters independently and ensure missing optional configuration fails clearly only
  when that adapter is enabled.
- Review extraction proposals against the independent-lifecycle criteria before implementation.
- Keep active work and unresolved decisions traceable to GitHub Issues while repository documents
  describe durable, accepted behavior.
