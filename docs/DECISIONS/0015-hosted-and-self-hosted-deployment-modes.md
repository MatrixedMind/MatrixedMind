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

The initial hosted MatrixedMind deployment will reuse an existing shared external HTTPS load
balancer and static IP. This avoids the recurring cost of a second load balancer.

Self-hosted Terraform will support two mutually exclusive deployment modes:

- Direct public Cloud Run, without an external load balancer managed by MatrixedMind Terraform.
- Cloud Run behind an external load balancer, with Cloud Run ingress configured to block direct
  public access that bypasses the load balancer.

Only one mode may be selected for an environment. The hosted MatrixedMind deployment selects the
external-load-balancer mode and reuses existing edge resources; that reuse is a deployment-specific
configuration, not a required self-hosted topology.

A Shared VPC with a separate edge project was considered. It is deferred because its project,
networking, IAM, and operational overhead is not justified at the current scale. It can be
reconsidered if stronger project isolation or centralized networking becomes necessary.

This ADR defines the intended topology and configuration contract. It does not claim that the
Terraform modes, load-balancer route, DNS, or Cloud Run ingress restrictions are implemented or
verified yet.

## Consequences

### Positive

- Avoids a second recurring load-balancer cost for the initial hosted deployment.
- Preserves a lower-cost direct Cloud Run option for self-hosters.
- Makes the secure load-balancer path explicit and prevents accidental simultaneous modes.
- Keeps hosted edge-resource reuse separate from portable self-hosted configuration.

### Negative

- The hosted deployment depends on shared edge infrastructure in an existing project.
- Terraform must validate mutually exclusive modes and handle externally supplied edge resources.
- Operators choosing the load-balancer mode must configure and verify that direct Cloud Run ingress
  is blocked.

## Verification expectations

- Terraform rejects configurations that select both modes or neither mode.
- Direct mode exposes the intended Cloud Run URL without creating load-balancer resources.
- External-load-balancer mode routes through the configured load balancer and has no unintended
  direct public Cloud Run path.
- The hosted environment uses the existing shared load balancer and static IP without creating a
  second load balancer.
