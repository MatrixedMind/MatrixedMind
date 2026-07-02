# 0004: Deploy to GCP Cloud Run with Terraform

## Status

Accepted

## Context

MatrixedMind should have a straightforward path from local development to a hosted dev deployment. The deployment target should support containers, scale down when idle, and avoid long-lived service-account keys.

## Decision

Deploy MatrixedMind to Cloud Run. Build and store images in Artifact Registry. Manage infrastructure with Terraform. Store Terraform state in a versioned GCS backend. Store secrets in Secret Manager. Use GitHub Actions with Workload Identity Federation for CI/CD authentication.

## Consequences

### Positive

- Cloud Run fits a single containerized FastAPI service.
- Terraform makes infrastructure reviewable and repeatable.
- Workload Identity Federation avoids service-account keys.
- Secret Manager provides a clear cloud secret boundary.

### Negative

- Terraform bootstrap needs careful state handling.
- IAM setup can be tedious.
- GCP-specific deployment code should remain isolated from core app behavior.
