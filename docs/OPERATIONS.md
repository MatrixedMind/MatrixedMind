# Operations

## Operating model

MatrixedMind is intended to run as one containerized FastAPI service on Cloud Run, with infrastructure managed by Terraform and images stored in Artifact Registry.

## Local operations

Start the local stack:

```bash
docker compose up -d
```

Check container status:

```bash
docker compose ps
```

Stop the local stack:

```bash
docker compose down
```

## Health checks

The base health endpoint is:

```text
/health
```

Milestone 1 should add a database-aware readiness check or expand health verification so local MongoDB connectivity can be proven.

## Terraform

Terraform roots live under:

```text
infra/terraform/envs/{dev,prod}
```

Reusable modules should live under:

```text
infra/terraform/modules/*
```

Required checks for Terraform changes:

```bash
terraform fmt -check
terraform validate
terraform plan
```

Terraform state should use a versioned GCS backend. Do not migrate or rewrite the state without an explicit plan.

## Deployment

The intended deployment flow is:

1. GitHub Actions authenticates to GCP with Workload Identity Federation.
2. CI builds the Docker image.
3. CI pushes the image to Artifact Registry.
4. Terraform deploys or updates Cloud Run.
5. A post-deploy health check confirms that the service responds.

## Secrets

Cloud secrets belong in Secret Manager. Production Terraform must reference explicit secret versions, not `latest`.

## Logs and troubleshooting

Use Cloud Run logs for request and application errors. Local development should use container logs or direct Uvicorn output:

```bash
docker compose logs api
```

## Backup and recovery

Milestone 7 must provide import/export, so content is portable and recoverable before the app is treated as durable personal infrastructure.

## Rollback

Before production use, define rollback steps for:

- Reverting a Cloud Run revision.
- Restoring configuration.
- Recovering exported content.
- Reverting Terraform changes safely.
