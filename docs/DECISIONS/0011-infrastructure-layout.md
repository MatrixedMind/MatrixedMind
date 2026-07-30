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
  edge/
  modules/
  envs/
    dev/
    prod/
```

`bootstrap` is only for resources needed before normal environment configuration can run.

`edge` owns the separately planned shared load-balancer frontend. Its preparation mode creates
DNS-authorized certificates, SNI mappings, host routing, and replacement proxies without mutating
the live frontend. After a separately approved in-place migration, its adoption mode can manage the
existing backend and forwarding rules under explicit confirmation gates without absorbing those
resources into an application-environment root.

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
- A plan can be generated independently for each application environment and the shared edge.
