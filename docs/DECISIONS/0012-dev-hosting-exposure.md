# 0012: Keep Hosted Development Access Restricted by Default

## Status

Accepted

## Context

The first hosted MatrixedMind environment exists for development and verification, not public launch.

## Decision

The hosted development environment should require authenticated access by default.

Do not make the hosted development environment openly reachable unless there is a deliberate temporary review need. Any temporary exception must be documented and removed after the review need is gone.

A public production launch requires a separate decision after application authentication, authorization, and crawler metadata behavior are implemented and tested.

## Consequences

### Positive

- Reduces the chance of exposing pre-MVP personal wiki data.
- Keeps public launch as an intentional later step.
- Fits the project rule that production auth shortcuts are not acceptable.

### Negative

- Quick demos require a little more setup.
- Access configuration needs to be documented during deployment work.

## Verification expectations

- The dev deployment documents its access setting.
- The health check is verified through the intended access path.
- Any temporary open-access exception is documented and removed when no longer needed.
