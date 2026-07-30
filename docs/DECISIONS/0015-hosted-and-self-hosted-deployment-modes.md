# 0015: Define Hosted and Self-Hosted Deployment Modes

## Status

Accepted

## Context

MatrixedMind needs a custom-domain deployment without adding unnecessary recurring infrastructure
cost. An existing GCP project already has a shared external HTTPS load balancer and static IP that
can route another service.

Self-hosters may have different cost, domain, and isolation requirements. Terraform therefore needs
an explicit deployment choice rather than assuming that every installation has an external load
balancer or that every Cloud Run service should remain directly public.

## Decision

The official hosted MatrixedMind deployment uses three separate GCP projects:

- a shared edge project for the external HTTPS load-balancer frontend, static IP, certificate, and
  URL map;
- a private development project for development application resources; and
- a production project for the production Cloud Run service, serverless NEG, backend service,
  database, secrets, and other application resources.

The hosted deployment will reuse the existing shared edge and static IP. The edge project must use
the global external Application Load Balancer mode before its URL map can reference the production
project's backend service. Modernizing or importing the existing edge resources requires a separate,
reviewed cutover; application Terraform must not replace or mutate them implicitly.

Self-hosted Terraform will support two mutually exclusive deployment modes:

- Direct public Cloud Run, without an external load balancer managed by MatrixedMind Terraform.
- Cloud Run behind an external load balancer, with Cloud Run ingress configured to block direct
  public access that bypasses the load balancer.

Only one mode may be selected for an environment. In external-load-balancer mode, the Cloud Run
service, serverless NEG, backend service, and optional Cloud Armor policy stay together in the
application project. A same-organization global external Application Load Balancer can reference
that backend service from a separate edge project after an explicit administrator receives
`roles/compute.loadBalancerServiceUser` in the application project. The application Terraform
module does not create or modify a frontend, static IP, certificate, URL map, or DNS record.

The hosted MatrixedMind deployment selects the external-load-balancer mode in its production root.
The development root remains private. Reusing separate edge resources is a deployment-specific
configuration, not a required self-hosted topology.

A Shared VPC is not required for this same-organization global cross-project reference and remains
deferred. It can be reconsidered if later networking requirements justify its additional IAM and
operational overhead.

The three exclusive Terraform invocation modes and their ingress/IAM contracts are implemented and
locally tested. A separately stateful edge root implements non-disruptive certificate, SNI, routing,
and proxy preparation plus explicitly confirmed post-migration adoption of the existing backend and
forwarding rules. This ADR defines the durable topology; see `docs/OPERATIONS.md` for the current
tested deployment and activation status.

## Consequences

### Positive

- Avoids a second recurring load-balancer cost for the initial hosted deployment.
- Isolates shared edge, private development, and production application resources.
- Preserves a lower-cost direct Cloud Run option for self-hosters.
- Makes the secure load-balancer path explicit and prevents accidental simultaneous modes.
- Keeps hosted edge-resource reuse separate from portable self-hosted configuration.

### Negative

- The hosted deployment depends on shared edge infrastructure and cross-project IAM in the same
  organization.
- The existing classic load balancer requires a separately validated modernization and cutover
  before cross-project service referencing is available.
- Terraform must validate mutually exclusive modes and handle externally supplied edge resources.
- Operators choosing the load-balancer mode must configure and verify that direct Cloud Run ingress
  is blocked.

## Verification expectations

- Terraform rejects configurations that select both modes or neither mode.
- Direct mode exposes the intended Cloud Run URL without creating load-balancer resources.
- External-load-balancer mode routes through the configured load balancer and has no unintended
  direct public Cloud Run path.
- The production backend service and serverless NEG remain in the production application project,
  while the edge URL map references the backend through its fully qualified resource name.
- The hosted environment uses the existing shared load balancer and static IP without creating a
  second load balancer.
