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

`LLM_TOKEN_PEPPER` is retained here only because the currently deployed Terraform contract still
provisions and injects it. The application no longer consumes it: personal access tokens are
high-entropy random credentials stored by one-way hash. Removing the secret, IAM binding, version
input, and Cloud Run environment reference is a separate reviewed infrastructure migration.

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
and exposure. The deploy workflow owns the immutable image revision, while Cloud Run's `client`
and `client_version` fields are operational deploy metadata and are ignored by Terraform. Run and
apply a reviewed Terraform plan for the Terraform-owned changes.

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

The approved read-only observer scope is `matrixed-mind-dev` and `matrixedmind-prod`; the shared
edge project is excluded. For each investigation, state one environment, one project, a short UTC
time range, and an objective. Start with Cloud Run service metadata and a narrow Cloud Logging
filter for the named service and severity or status class; use a small result limit and sanitize
identifiers, token-like values, request bodies, and record content from any report. Correlate an
error with Cloud Monitoring request-count, latency, and alert-policy metadata before widening the
time range. The observer must not deploy, change IAM, create credentials, inspect secrets, or
mutate Cloud Run or Firestore. Stop when the requested evidence is sufficient rather than polling
unchanged state.

Each environment's Terraform root now manages one keyless observer service account, grants it only
`roles/logging.viewer`, `roles/monitoring.viewer`,
and `roles/run.viewer` in that environment project, and grants the approved impersonating principal
`roles/iam.serviceAccountTokenCreator` on that observer account alone. No user-managed keys exist.
The development and production impersonation smokes read Cloud Run metadata, a bounded log window,
and monitoring metadata successfully without mutation.

Terraform manages two Cloud Run policies per environment: a 5xx request-rate policy and a p99
latency policy. With the apply-time `operational_notification_email`, Terraform creates the
conventional MatrixedMind environment channel and wires its generated resource name directly into
the policies and budget. Externally managed channel resource names are optional reuse inputs;
budget reuse must be verified read-only as email channels and may total no more than five. Budgets
never fall back to unreviewed billing IAM recipients. The recipient is not committed, but
Terraform state retains it. The initial latency threshold is 10,000 milliseconds; thresholds are
not a production tuning decision. Tune them only after deployed request-volume, error-rate, and
latency data is reviewed. A documented manual check confirmed that both policies are enabled and
wired to the generated channel in each environment. It did not force a synthetic incident or
delivery.

For an existing development budget configuration, treat the new enable flag as an audited
configuration migration: set `enable_billing_budget = true` alongside the existing billing account,
amount, and an apply-time notification destination (or verified external email channel) before
running any plan or apply. Leaving the flag false while budget inputs are populated is intentionally
invalid, preventing an unreviewed plan from silently destroying the budget. Do not add literal
billing IDs or recipient identities to version-controlled example files.

## Backup and recovery

Import/export remains important for portability and recovery, but it is now deferred until after the secure Cloud MVP path unless recovery requirements pull it forward. Before MatrixedMind is treated as durable personal infrastructure, either import/export or another validated backup/restore path must exist and be tested.

Firestore point-in-time recovery is enabled in the Terraform database definitions. For an
Enterprise database with MongoDB compatibility, the supported PITR exercise is a
[`gcloud firestore databases clone`](https://cloud.google.com/sdk/gcloud/reference/firestore/databases/clone)
operation into a new database, not a scheduled-backup restore. Cloning and PITR are Preview
features; recheck the current Google Cloud contract before each exercise.

Use an isolated development target named
`matrixedmind-dev-restore-validation-<UTC-date-time>` in `matrixed-mind-dev`, containing only
owner-approved test data. Before requesting mutation approval, describe the source database and
record its location, edition, MongoDB data-access mode, PITR state, and `earliestVersionTime`
without recording its UID. Select a whole-minute RFC 3339 snapshot time that is in the past and
within the available PITR window. The audited clone command has this shape:

```bash
gcloud firestore databases clone \
  --project=matrixed-mind-dev \
  --source-database=projects/matrixed-mind-dev/databases/matrixedmind-spike \
  --snapshot-time=<approved-whole-minute-UTC-timestamp> \
  --destination-database=<approved-isolated-target>
```

Wait for the clone operation to complete; the target is not usable while the operation is in
progress. Then describe the target and verify its location, edition, MongoDB access mode, PITR and
delete-protection state, and cloned index readiness rather than assuming every source setting was
inherited. Do not change the normal development Cloud Run service or its `MONGO_URI`.

Use separate short-lived identities: a source-marker service account with `roles/datastore.user`
conditioned only to `matrixedmind-spike`, and a target-validator service account with the same role
conditioned only to the exact restore target. The source identity seeds one fixed, non-sensitive
marker in a dedicated `restore_validation` collection before the selected source timestamp and
removes that exact marker only after successful evidence collection. Against the completed clone,
the target identity proves the exact marker and payload are present, runs a database ping and the
Firestore repository-contract suite, and preserves sanitized results. The harness rejects any
database other than the exact development source or a correctly prefixed isolated restore target,
and it requires Firestore's TLS/OIDC connection options. Never point the suite at production; it
deletes its test documents from the `records` collection.

After successful validation, stop and present a separate destructive-cleanup plan for approval.
That plan removes the target-only IAM binding and validation job, describes the target again,
verifies its exact name and delete-protection state, captures its current ETag, and uses
[`gcloud firestore databases delete`](https://cloud.google.com/sdk/gcloud/reference/firestore/databases/delete)
with `--etag=<current-target-etag>` so cleanup fails closed on concurrent change. If target delete
protection is enabled, disabling it is a separately reviewed mutation. If validation or cleanup
preconditions fail, stop access, preserve the target for diagnosis, and leave the source database
untouched except for the explicitly approved test marker. Terraform does not currently expose a
declarative PITR clone operation, so the exact clone and cleanup commands require explicit audited
approval even though they are not Terraform state actions. Clone approval never implies cleanup
approval.

On 2026-08-12, the approved source phase seeded marker `cloud-mvp-closeout-20260812` in development
and selected `2026-08-12T21:18:00Z` as the safe whole-minute source timestamp. PITR was enabled and
the timestamp was later than `earliestVersionTime`. The isolated clone completed successfully and
all five cloned MongoDB-compatible indexes reported `READY`. Two early target runs returned only
sanitized database-operation failures, so access was removed and the target was preserved.

The follow-up diagnostic image emits only fixed stages and categories, suppresses repository-test
output, and preserves a primary operation error across best-effort client teardown. Execution
`matrixedmind-closeout-target-q4sgm` classified the failure as
`marker-read/authorization-failure`. The prior executions had waited only 20 seconds after adding
the database-specific IAM grant; Firestore IAM changes can remain cached for up to five minutes.
The next bounded attempt used the same narrow grant, waited the full 300 seconds, and execution
`matrixedmind-closeout-target-fvwcg` completed successfully at
`2026-08-13T00:29:38.223107Z`. It proved the exact cloned marker and payload, database ping, and the
Firestore repository-contract suite without emitting a URI, token, credential, exception message,
or repository-test output. The target binding was removed immediately and verified absent.

The separately approved cleanup completed on 2026-08-13. Execution
`matrixedmind-closeout-source-dhldm` deleted exactly the one source marker. Both temporary jobs,
their exact IAM bindings, and both temporary service accounts were removed and verified absent.
The isolated target was deleted at `2026-08-13T01:02:34.067558Z`, and the deleted-database record
preserves its expected previous ID.
The source database remains present and delete-protected; the normal development service remains on
ready revision `matrixedmind-dev-00013-br6` with 100% traffic. Production still reports all five
MongoDB-compatible composite indexes ready. A fresh normal locked development plan reported zero
managed or output changes, and Terraform state remained at serial 18.

### Non-production secret-rotation test

After a reviewed cloud-mutation plan is explicitly approved, test rotation in development only:

1. Create a new value outside the repository and add it as a new Secret Manager version.
2. Change only the matching explicit numeric Terraform version input; never use `latest`.
3. Review the plan, apply it, and confirm the resulting Cloud Run revision uses that number.
4. Run the authenticated `/health` and `/ready` checks and one scoped LLM-token request using a
   deliberately non-production token.
5. Confirm the prior token or secret behavior is understood before disabling its old version;
   record the rollback version and restore it through a reviewed Terraform plan if needed.

For the bounded smoke, use a one-off Cloud Run Job with the source-marker service account, which has
`roles/datastore.user` conditioned to the development database and `roles/run.invoker` on only the
development service. Run `scripts/dev_secret_rotation_smoke.py` from the reviewed Firestore test
image. It creates a uniquely named read-only token for the `closeout-smoke` space, stores only its
SHA-256 hash, obtains a Cloud Run identity token from the metadata server, and keeps the platform
token in `X-Serverless-Authorization` so the app-level LLM token remains in `Authorization`. It
checks authenticated health and readiness, performs the scoped LLM list request, revokes the exact
test token, and proves the same request then returns `401`. The harness never prints either token,
the database URI, response bodies, or authorization headers. Remove the temporary job and IAM
bindings after evidence is captured; retain the revoked token record as the non-production audit
artifact.

`APP_SECRET_KEY` remains in the currently deployed Terraform contract but is no longer an
application setting. MatrixedMind browser sessions use random opaque credentials persisted only by
hash, so rotating this legacy secret does not rotate or invalidate browser sessions. Removing its
Secret Manager resource, IAM binding, version input, and Cloud Run environment reference is a
separate reviewed infrastructure migration.

The development rotation exercise completed on 2026-08-12. Secret version 2 is active on ready
revision `matrixedmind-dev-00013-br6`, rollback version 1 remains enabled, authenticated health and
readiness passed, and the bounded LLM smoke proved scoped access, exact revocation, and rejection
after revocation. The initial version-2 revision failed closed with no traffic because its startup
command attempted a runtime dependency sync and exceeded 512 MiB; the corrected production image
uses `uv run --no-sync`. Full sanitized evidence is in the
[Cloud MVP verification follow-up register](CLOUD_MVP_VERIFICATION_FOLLOW_UP.md). Secret values,
token values, and service-account keys must never be placed in Terraform, plans, logs, or this
repository.

### Cost and connectivity review

A bounded production review on 2026-07-31 found 67 billable read units, 33 billable write units,
6,387 bytes of current data-plus-index storage, and no scanned-document or scanned-index-entry
units over the preceding seven days. Both environments retain five intentional composite indexes.
All development indexes were ready; production initially reported three ready and two still
creating even though their associated operations reported complete. A bounded read-only recheck at
`2026-08-13T00:32:14Z` reported all five production MongoDB-compatible composite indexes `READY`,
with no production mutation. Full evidence is tracked in the
[Cloud MVP verification follow-up register](CLOUD_MVP_VERIFICATION_FOLLOW_UP.md). Current activity
is too small to justify schema or index changes; keep record bodies and embedded revisions bounded
and repeat the review after material traffic, query, schema, or retention growth.

The same seven-day log review found 30 production LLM API requests, no development LLM requests,
and no 429 responses. Retain the current process-local limit of 60 requests per 60 seconds. Revisit
the value—and distributed enforcement—when sustained traffic or multi-instance scaling provides
representative evidence.

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

The approved observer scope is `matrixed-mind-dev` and `matrixedmind-prod`; the shared-edge project
remains excluded. Local operations must use the canonical organization-controlled Terraform
operator, verify gcloud, ADC, provider, backend, and impersonation identities independently, and
stop on a mismatch. Account-specific identities belong in local configuration and audited plans,
not committed defaults. The agent chooses routine Terraform identifiers and the temporary
restore-target naming convention above; the owner decides live destinations, spending limits,
security boundaries, data-safety actions, and the complete mutation plan.

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
