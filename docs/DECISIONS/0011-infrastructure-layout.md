# 0011: Use Environment Infrastructure Roots

## Status

Accepted

## Context

MatrixedMind needs a predictable infrastructure layout so development and production configuration do not get mixed together.

## Decision

Use this layout:

```text
infra/terraform/
  bootstrap/
  modules/
  envs/
    dev/
    prod/
```

`bootstrap` is only for resources needed before normal environment configuration can run.

`envs/dev` owns the private hosted development environment.

`envs/prod` owns production application resources in a separate production project. Edge resources
such as a shared load-balancer frontend are not part of either application-environment root.

`modules` holds small reusable components. Start small and only add module boundaries when there is a repeated pattern.

## Consequences

### Positive

- Development, production, and shared-edge planning stay separate.
- Bootstrap work stays separate from normal environment changes.
- The project has a clear location for reusable infrastructure components.

### Negative

- There is one extra bootstrap step before the first environment can be initialized.
- Some backend configuration will be repeated across environment roots.

## Verification expectations

- Formatting checks pass for all infrastructure files.
- Validation passes for initialized roots.
- A plan can be generated independently for each application environment.
