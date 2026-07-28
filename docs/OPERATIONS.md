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

Bootstrap resources live under:

```text
infra/terraform/bootstrap
```

The bootstrap root creates the private, versioned GCS bucket used by environment backends. The owner must create or select the GCP project, link billing, and confirm the Service Usage API is available before running it.

```bash
cd infra/terraform/bootstrap
terraform init
terraform apply -var-file=terraform.tfvars
```

Initialize each environment with an explicit backend bucket value (do not hard-code bucket names in `backend.tf`):

```bash
cd infra/terraform/envs/dev
terraform init -backend-config="bucket=<your-gcp-project-id>-tf-state"
terraform plan -var-file=terraform.tfvars
```

Use the same pattern for `envs/prod` with the production bucket.

Reusable modules should live under:

```text
infra/terraform/modules/*
```

The current modules own Artifact Registry, runtime Secret Manager entries, and Cloud Run service
configuration. `envs/dev/migrations.tf` preserves the milestone 7 resource addresses while moving
those resources into modules; review the first plan carefully and do not remove the migration
blocks until every existing state has applied the moves.

Required checks for Terraform changes:

```bash
terraform fmt -check
terraform validate
terraform plan
```

The dev root can apply foundational infrastructure before the app is deployable. Keep
`enable_cloud_run_service = false` until the application image and both numbered runtime secret
versions exist. Keep
`enable_firestore_spike_job = false` until the dedicated test image exists. Keep
`allow_unauthenticated_cloud_run = false` until MatrixedMind enforces app-level auth for sensitive
routes.

Firestore uses passwordless GCP OIDC. Terraform derives the non-secret URI, grants the Cloud Run
service accounts `roles/datastore.user`, and creates the MongoDB-compatible indexes. The application
uses `MONGO_ENSURE_INDEXES=false` in GCP so index administration remains an infrastructure concern.
See [`FIRESTORE_MONGO_SPIKE.md`](FIRESTORE_MONGO_SPIKE.md) for the image, job, and execution commands.

Terraform state should use a versioned GCS backend. Do not migrate or rewrite the state without an explicit plan.

## Deployment

### One-time owner setup

Copy the examples without committing the real files:

```bash
cp infra/terraform/bootstrap/terraform.tfvars.example infra/terraform/bootstrap/terraform.tfvars
cp infra/terraform/envs/dev/terraform.tfvars.example infra/terraform/envs/dev/terraform.tfvars
```

Create the versioned backend, then initialize the development root:

```bash
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap plan -var-file=terraform.tfvars -out=bootstrap.tfplan
terraform -chdir=infra/terraform/bootstrap apply bootstrap.tfplan
terraform -chdir=infra/terraform/envs/dev init \
  -backend-config="bucket=<your-gcp-project-id>-tf-state"
```

Apply the foundation with `enable_cloud_run_service = false`, then add the two secret payloads
without printing or committing them:

```bash
terraform -chdir=infra/terraform/envs/dev plan -var-file=terraform.tfvars -out=foundation.tfplan
terraform -chdir=infra/terraform/envs/dev apply foundation.tfplan
gcloud secrets versions add matrixedmind-dev-app-secret-key --data-file=-
gcloud secrets versions add matrixedmind-dev-llm-token-pepper --data-file=-
```

Build and push the first immutable image:

```bash
export MATRIXEDMIND_IMAGE="<region>-docker.pkg.dev/<project>/matrixedmind/matrixedmind:$(git rev-parse HEAD)"
gcloud auth configure-docker "<region>-docker.pkg.dev"
docker build --tag "$MATRIXEDMIND_IMAGE" .
docker push "$MATRIXEDMIND_IMAGE"
```

Set `container_image` to that URI, set the two secret-version variables to the numbered versions
that were created, and set `enable_cloud_run_service = true`. Keep
`allow_unauthenticated_cloud_run = false` for the restricted development deployment. Review and
apply the service plan:

```bash
terraform -chdir=infra/terraform/envs/dev plan -var-file=terraform.tfvars -out=service.tfplan
terraform -chdir=infra/terraform/envs/dev apply service.tfplan
```

Do not commit `*.tfplan`; remove local plan files after use.

### GitHub deployment configuration

Create a protected GitHub environment named `development` and configure these repository or
environment variables from Terraform outputs and the selected GCP project:

```text
GCP_ARTIFACT_REGISTRY_REPOSITORY=matrixedmind
GCP_CLOUD_RUN_SERVICE=matrixedmind-dev
GCP_DEPLOYER_SERVICE_ACCOUNT=<github_deployer_service_account_email output>
GCP_PROJECT_ID=<project ID>
GCP_REGION=<region>
GCP_WORKLOAD_IDENTITY_PROVIDER=<workload_identity_provider output>
```

No service-account JSON key or runtime secret belongs in GitHub. The `Deploy development` workflow
runs after successful CI on `main` and can also be dispatched manually from `main`. It:

1. GitHub Actions authenticates to GCP with Workload Identity Federation.
2. Builds and pushes a commit-tagged Docker image to Artifact Registry.
3. Updates only the Cloud Run image, leaving Terraform-owned configuration unchanged.
4. Calls `/health` and `/ready` with the deployer service account's Cloud Run identity token.

Terraform remains authoritative for environment variables, secret versions, probes, IAM, scaling,
and exposure. Run and apply a reviewed Terraform plan for those changes.

### Manual verification

For a private service, mint an audience-bound identity token and check both endpoints:

```bash
export MATRIXEDMIND_URL="$(gcloud run services describe matrixedmind-dev \
  --region=<region> --format='value(status.url)')"
export MATRIXEDMIND_ID_TOKEN="$(gcloud auth print-identity-token --audiences="$MATRIXEDMIND_URL")"
curl --fail --header "Authorization: Bearer $MATRIXEDMIND_ID_TOKEN" "$MATRIXEDMIND_URL/health"
curl --fail --header "Authorization: Bearer $MATRIXEDMIND_ID_TOKEN" "$MATRIXEDMIND_URL/ready"
```

`/health` proves the revision is serving. `/ready` proves the runtime identity can reach the hosted
Firestore MongoDB-compatible database.

## Secrets

Cloud secrets belong in Secret Manager. Terraform references explicit numeric versions, never
`latest`. Rotating a value means adding a new secret version, updating the matching Terraform
version variable, reviewing the plan, and applying it so Cloud Run creates a new revision. Disable
the prior version only after the new revision passes both endpoint checks.

## Logs and troubleshooting

Use Cloud Run logs for request and application errors. Local development should use container logs or direct Uvicorn output:

```bash
docker compose logs api
```

## Backup and recovery

Import/export remains important for portability and recovery, but it is now deferred until after the secure Cloud MVP path unless recovery requirements pull it forward. Before MatrixedMind is treated as durable personal infrastructure, either import/export or another validated backup/restore path must exist and be tested.

## Rollback

To roll back application code, deploy a previously known-good immutable Artifact Registry image:

```bash
gcloud run services update matrixedmind-dev \
  --region=<region> \
  --image=<region>-docker.pkg.dev/<project>/matrixedmind/matrixedmind:<known-good-sha>
```

For configuration or secret rollback, revert the Terraform input to the previous explicit value or
secret version, review `terraform plan`, and apply it. Do not edit the Cloud Run configuration by
hand because that creates Terraform drift.

Before production use, additionally define and test steps for:

- Recovering exported content.
- Reverting Terraform changes safely.
