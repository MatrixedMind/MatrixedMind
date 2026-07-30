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

Application-environment Terraform roots live under:

```text
infra/terraform/envs/{dev,prod}
```

The separately planned shared-edge root lives under:

```text
infra/terraform/edge
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

Initialize `edge` with its own remote-state prefix after the production backend service exists:

```bash
terraform -chdir=infra/terraform/edge init \
  -backend-config="bucket=<your-edge-state-bucket>"
terraform -chdir=infra/terraform/edge plan -var-file=terraform.tfvars
```

The edge root defaults to non-disruptive preparation: it does not manage the existing backend or
forwarding rules and cannot compete for the live static IP. It prepares DNS authorizations and
Certificate Manager certificates for both hostnames, exact SNI certificate-map entries, separate
host routes for the existing site and MatrixedMind, and replacement HTTP/HTTPS proxies. Domain
owners must add the two output CNAME records and both certificates must become `ACTIVE` before any
frontend migration.

The existing classic backend and forwarding rules require Google's staged in-place migration to
`EXTERNAL_MANAGED`; that externally coordinated operation is deliberately not represented as a
single Terraform apply. Only after the migration and target switch have been verified may an
operator import those existing resources and set `manage_migrated_frontend = true`,
`frontend_migration_confirmed = true`, and `certificates_active_confirmed = true`. This adoption
path reuses the existing forwarding-rule names and static IP instead of creating a second load
balancer. The migration, DNS records, imports, and hosted smoke tests were completed on
2026-07-30; the verified activation record appears later in this document.

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

The dev root can apply foundational infrastructure before the app is deployable. It always passes
the module's `private` invocation mode and never creates load-balancer integration resources. Keep
`enable_cloud_run_service = false` until the application image and both numbered runtime secret
versions exist. Keep
`enable_firestore_spike_job = false` until the dedicated test image exists.

The module accepts exactly one invocation mode:

- `private`: current restricted staging behavior; no `allUsers` invoker and no load-balancer NEG.
- `direct`: self-hosted direct public Cloud Run; public invoker with normal Cloud Run ingress.
- `external_load_balancer`: the Invoker IAM check is disabled without an `allUsers` binding, ingress
  is restricted to internal and Cloud Load Balancing traffic, and a serverless NEG and backend
  service are created in the application project. This is compatible with Domain Restricted
  Sharing; app-level bearer authentication remains the primary LLM API boundary.

The production root supports `private` staging and `external_load_balancer`; direct public Cloud Run
remains available through the reusable module for self-hosted compositions. In hosted mode, the
production root exports a fully qualified backend-service reference and grants only configured
edge administrators `roles/compute.loadBalancerServiceUser`. It does not alter an existing URL map,
certificate, static IP, frontend, or DNS record. Those separate shared-edge changes require a
reviewed plan and explicit approval. A non-null
`openai_action_address_group_name` attaches a Cloud Armor policy to the MatrixedMind backend. The
policy allows a reviewed Cloud Armor Enterprise address group to `/api/llm/*`, denies other network
sources from those paths, and allows non-LLM paths to continue to application-level controls. Keep
the reference null unless Cloud Armor Enterprise cost, the published ChatGPT-integration range feed,
and its refresh procedure have been reviewed; the scoped bearer token remains mandatory regardless
of network policy.

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
docker build --platform linux/amd64 --tag "$MATRIXEDMIND_IMAGE" .
docker push "$MATRIXEDMIND_IMAGE"
```

For an image intended for hosted use, embed the exact source revision in the same build:

```bash
docker build --platform linux/amd64 \
  --build-arg SOURCE_REVISION="$(git rev-parse HEAD)" \
  --tag "$MATRIXEDMIND_IMAGE" .
```

The visible AGPL source offer combines that immutable revision with the configured public
`SOURCE_REPOSITORY_URL`. Verify the resulting link before hosted activation.

The explicit platform is required when building from Apple Silicon because Cloud Run requires an
image manifest with Linux AMD64 support. GitHub's Ubuntu deployment runner already builds AMD64.

Set `container_image` to that URI, set the two secret-version variables to the numbered versions
that were created, and set `enable_cloud_run_service = true`. The development root remains private.
Review and apply the service plan:

```bash
terraform -chdir=infra/terraform/envs/dev plan -var-file=terraform.tfvars -out=service.tfplan
terraform -chdir=infra/terraform/envs/dev apply service.tfplan
```

The production foundation was first verified with an IAM-private Cloud Run staging service on
2026-07-29. The hosted topology was then activated and verified through its custom domain on
2026-07-30 UTC. The shared global external Application Load Balancer retained its static IP and
existing co-hosted route, both managed certificates became active, and Terraform adopted the live
frontend with a no-change drift plan. `/health`, `/ready`, and `/openapi-llm.json` returned `200`
through the custom domain, the protected root returned the expected application-level `401`, and
the direct public `run.app` health path returned `404`. HTTP requests for both hostnames redirected
to HTTPS, and the existing co-hosted site continued to return `200` over HTTPS.

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
3. Embeds that verified commit in the image for the hosted source-offer link.
4. Updates only the Cloud Run image, leaving Terraform-owned configuration unchanged.
5. Calls `/health` and `/ready` with the deployer service account's Cloud Run identity token.

Terraform remains authoritative for environment variables, secret versions, probes, IAM, scaling,
and exposure. Run and apply a reviewed Terraform plan for those changes.

### Manual verification

For a private service, start Google Cloud's authenticated local proxy:

```bash
gcloud run services proxy matrixedmind-dev --project=<project> --region=<region> --port=18085
```

In another terminal, check both endpoints through the proxy:

```bash
curl --fail http://127.0.0.1:18085/health
curl --fail http://127.0.0.1:18085/ready
```

`/health` proves the revision is serving. `/ready` proves the runtime identity can reach the hosted
Firestore MongoDB-compatible database.

The first development deployment was verified on 2026-07-28 with revision
`matrixedmind-dev-00002-fz4`. `/health` returned `{"status":"ok","env":"production"}`, `/ready`
returned `{"status":"ok","mongo":"ok"}`, direct unauthenticated platform access returned `403`,
and an authenticated request to `/` returned MatrixedMind's expected production-auth `401`.

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

### Hosted log review

Use the read-only observer only after the development and production project IDs have been
confirmed by the owner. For each investigation, state one environment, one project, a short UTC
time range, and an objective. Start with Cloud Run service metadata and a narrow Cloud Logging
filter for the named service and severity or status class; use a small result limit and sanitize
identifiers, token-like values, request bodies, and record content from any report. Correlate an
error with Cloud Monitoring request-count, latency, and alert-policy metadata before widening the
time range. The observer must not deploy, change IAM, create credentials, inspect secrets, or
mutate Cloud Run or Firestore. Stop when the requested evidence is sufficient rather than polling
unchanged state.

Terraform declares two optional Cloud Run policies per environment: a 5xx request-rate policy and
a p99 latency policy. Both policies and budget alerts are disabled by default; development budget
creation also requires an explicit enable flag, billing account, amount, and existing reviewed
Monitoring notification-channel resource names. Budgets never fall back to unreviewed billing IAM recipients.
The initial latency threshold is
10,000 milliseconds; thresholds are not a production tuning decision. Tune them only after
deployed request-volume, error-rate, and latency data is reviewed. A controlled alert test or documented manual check remains required
before treating either policy as verified.

For an existing development budget configuration, treat the new enable flag as an audited
configuration migration: set `enable_billing_budget = true` alongside the existing billing account,
amount, and reviewed notification-channel resource names before running any plan or apply. Leaving
the flag false while any of those legacy inputs are populated is intentionally invalid, preventing
an unreviewed plan from silently destroying the budget. Do not add literal billing IDs or recipient
identities to version-controlled example files.

## Backup and recovery

Import/export remains important for portability and recovery, but it is now deferred until after the secure Cloud MVP path unless recovery requirements pull it forward. Before MatrixedMind is treated as durable personal infrastructure, either import/export or another validated backup/restore path must exist and be tested.

Firestore point-in-time recovery is enabled in the Terraform database definitions, but that is an
assumption, not a validated MatrixedMind restore procedure. A restore exercise must use a
non-production target, identify the source timestamp and target database/project, restore only
approved test data, run the repository contract/readiness checks, and document cleanup. The exact
current blocker is that no owner-confirmed development project ID, approved restoration target,
or approval for the live restore operation exists. Do not represent point-in-time recovery as a
tested backup until that exercise has passed.

### Non-production secret-rotation test

After a reviewed cloud-mutation plan is explicitly approved, test rotation in development only:

1. Create a new value outside the repository and add it as a new Secret Manager version.
2. Change only the matching explicit numeric Terraform version input; never use `latest`.
3. Review the plan, apply it, and confirm the resulting Cloud Run revision uses that number.
4. Run the authenticated `/health` and `/ready` checks and one scoped LLM-token request using a
   deliberately non-production token.
5. Confirm the prior token or secret behavior is understood before disabling its old version;
   record the rollback version and restore it through a reviewed Terraform plan if needed.

No rotation test has been run for Milestone 12. It is blocked by the same live-mutation approval
gate; secret values, token values, and service-account keys must never be placed in Terraform,
plans, logs, or this repository.

### Cost and connectivity review

Review Firestore cost from deployed metrics and billing data before changing limits: measure
document sizes, document reads/writes/deletes, index-write amplification, retention, and the
cost of the Firestore compatibility test job. Keep record bodies and embedded revisions bounded,
avoid unnecessary composite indexes, and revisit this review after material query, schema, or
retention changes. This is documentation of a review method, not evidence that current production
costs have been measured.

No MatrixedMind runtime dependency currently requires fixed-IP allowlisting, static egress, or
private connectivity. Do not add a NAT, private connector, or related routing cost now. Revisit
the decision before onboarding a dependency that requires source-IP allowlisting, private-only
addressing, VPC access, or an equivalent network boundary.

### Cloud mutation approval gate

Repository configuration and read-only discovery are approved. Before any live API enablement,
IAM grant, service-account creation, alert/budget creation, secret rotation, restore test, or
other cloud mutation, present one audited plan and wait for explicit approval. That plan must name
the exact APIs, confirmed project IDs, service-account identities, IAM roles, Terraform diff or
commands, verification steps, and rollback.

The unresolved inputs are the owner-confirmed development and production project IDs (the shared
edge project is excluded), Monitoring notification-channel recipients/resource names, billing
account IDs and budget amounts, observer service-account names and impersonation principals,
least-privilege IAM roles, and the approved non-production restoration target. No literal project
ID, email address, billing account, recipient, or IAM identity is inferred from this repository.

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
