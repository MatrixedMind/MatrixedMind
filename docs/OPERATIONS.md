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

The database-aware readiness endpoint is:

```text
/ready
```

`/ready` pings MongoDB through the app's MongoDB connection and returns a 503 response with `MongoDB is not ready` when the ping fails.

The Milestone 7 Firestore spike exercises the same application ping against Firestore MongoDB
compatibility. Its credential and runbook are intentionally separate from normal local operations;
see [`FIRESTORE_MONGO_SPIKE.md`](FIRESTORE_MONGO_SPIKE.md).

## Terraform

Terraform roots live under:

```text
infra/terraform/envs/{dev,prod}
```

Initialize each environment with an explicit backend bucket value (do not hard-code bucket names in `backend.tf`):

```bash
cd infra/terraform/envs/dev
terraform init -backend-config="bucket=<your-gcp-project-id>-tf-state"
```

Use the same pattern for `envs/prod` with the production bucket.

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

Import/export remains important for portability and recovery, but it is now deferred until after the secure Cloud MVP path unless recovery requirements pull it forward. Before MatrixedMind is treated as durable personal infrastructure, either import/export or another validated backup/restore path must exist and be tested.

## Rollback

Before production use, define rollback steps for:

- Reverting a Cloud Run revision.
- Restoring configuration.
- Recovering exported content.
- Reverting Terraform changes safely.
