# Firestore MongoDB Compatibility Spike

## Status

The compatibility suite and its GCP execution path are implemented and verified. Local MongoDB
remains the credential-free development baseline.

The suite deletes every document in the target `records` collection. Run it only against the
dedicated non-production database created by the dev Terraform root.

## Authentication decision

MatrixedMind uses passwordless service-account OIDC inside Google Cloud. Terraform creates the
Firestore Enterprise database and service accounts, grants `roles/datastore.user`, derives the
connection URI from the database UID, location, and ID, and injects that URI into Cloud Run. PyMongo
retrieves short-lived credentials from the Google Cloud metadata service.

The URI contains no username or password:

```text
mongodb://UID.LOCATION.firestore.goog:443/DATABASE_ID?loadBalanced=true&tls=true&retryWrites=false&authMechanism=MONGODB-OIDC&authMechanismProperties=ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE
```

This avoids generated SCRAM passwords, password rotation, manually assembled secret values, and
database credentials in Terraform state. SCRAM remains accepted by the test harness for external
diagnostics, but it is not the MatrixedMind Cloud Run runtime design.

The required connection options are:

- `loadBalanced=true` to disable topology discovery against the compatibility endpoint.
- `tls=true` to encrypt the connection.
- `retryWrites=false` because Firestore compatibility does not support retryable writes.
- `authMechanism=MONGODB-OIDC` with `ENVIRONMENT:gcp` and `TOKEN_RESOURCE:FIRESTORE` for Google
  Cloud service-account authentication.

## Terraform-managed resources

The dev root at `infra/terraform/envs/dev` manages:

- The Firestore Enterprise database with MongoDB-compatible data access.
- A Cloud Run runtime service account with `roles/datastore.user`.
- A separate compatibility-test service account with `roles/datastore.user`.
- MongoDB-compatible indexes for records, personal access tokens, and audit events.
- An optional Cloud Run service using the passwordless OIDC URI.
- An optional Cloud Run Job that executes the compatibility suite in GCP.

Indexes are an infrastructure concern in GCP. Terraform creates them before the job runs, while the
application uses `MONGO_ENSURE_INDEXES=false`. Local development retains the default value `true`,
so Docker MongoDB remains self-initializing.

## Owner prerequisites

Provide only non-secret configuration:

- GCP project ID.
- Preferred Cloud Run/Artifact Registry region; default `us-west1` for the development project.
- Preferred Firestore location; default `us-west1` so application compute and database traffic remain regional.
- Optional billing account ID and monthly budget amount if Terraform should create budget alerts.

Do not send service-account keys, access tokens, passwords, `.env` files, or credential JSON. Install
the Google Cloud CLI locally and authenticate Terraform through Application Default Credentials:

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project PROJECT_ID
gcloud config set project PROJECT_ID
```

The Terraform operator needs permission to enable APIs and manage the resources in the dev root.
For an owner-managed personal project, using a project Owner identity for the initial apply is the
simplest bootstrap. Tighten ongoing deployment permissions to the dedicated service accounts after
the foundation exists.

## Provision and run in GCP

Create local variable files from the committed examples. These files are ignored by Git:

```bash
cp infra/terraform/bootstrap/terraform.tfvars.example infra/terraform/bootstrap/terraform.tfvars
cp infra/terraform/envs/dev/terraform.tfvars.example infra/terraform/envs/dev/terraform.tfvars
```

Set `project_id` in both files and `github_repository = "MatrixedMind/MatrixedMind"` in the dev file.
Adjust region, Firestore location, and optional budget values if desired.

Create the remote-state bucket:

```bash
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap apply -var-file=terraform.tfvars
```

Initialize and apply the dev foundation with the Cloud Run resources disabled:

```bash
terraform -chdir=infra/terraform/envs/dev init \
  -backend-config="bucket=PROJECT_ID-tf-state"
terraform -chdir=infra/terraform/envs/dev plan -var-file=terraform.tfvars
terraform -chdir=infra/terraform/envs/dev apply -var-file=terraform.tfvars
```

If the dedicated database already exists, import it after initialization and before the first plan:

```bash
terraform -chdir=infra/terraform/envs/dev import \
  -var-file=terraform.tfvars \
  google_firestore_database.mongo_compatible \
  projects/PROJECT_ID/databases/DATABASE_ID
```

Build and push the dedicated test image after Artifact Registry exists:

```bash
gcloud auth configure-docker REGION-docker.pkg.dev
docker buildx build \
  --platform linux/amd64 \
  --file Dockerfile.firestore-test \
  --tag REGION-docker.pkg.dev/PROJECT_ID/matrixedmind/firestore-spike:COMMIT_SHA \
  --push \
  .
```

Set the following values in the ignored dev `terraform.tfvars`, then apply again:

```text
enable_firestore_spike_job = true
firestore_spike_image      = "REGION-docker.pkg.dev/PROJECT_ID/matrixedmind/firestore-spike:COMMIT_SHA"
```

Execute the job and wait for its result:

```bash
gcloud run jobs execute matrixedmind-firestore-spike \
  --region=REGION \
  --wait
```

Inspect sanitized logs if the job fails:

```bash
gcloud run jobs executions list \
  --job=matrixedmind-firestore-spike \
  --region=REGION
```

## What the suite verifies

- The reusable repository contract.
- Compound uniqueness for `(space, slug)` and adapter-level duplicate error mapping.
- PyMongo-generated and round-tripped BSON `ObjectId` values.
- Repository updates implemented with `update_one` and `$set`, including revision creation.
- Stable `created_at`, then `_id`, sorting for child lists.
- A direct database ping and the application `MongoConnection.ping` readiness path.

## Current result record

As of 2026-07-28:

- Local MongoDB and credential-free quality checks: passed; `123 passed, 6 expected Firestore
  skips`, with Ruff, mypy, pre-commit, and both Terraform roots valid.
- Terraform bootstrap and dev foundation: applied successfully in `us-west1`; the pre-existing
  protected Enterprise MongoDB-compatible database was imported without replacement, PITR was
  enabled, and the final foundation plan contained no destroys.
- Firestore test image: `firestore-spike:8e8a9731c796`, built for `linux/amd64` and pushed to the
  `us-west1` Artifact Registry repository.
- Cloud Run Job execution `matrixedmind-firestore-spike-9vqrr`: passed all six tests in 2.67 seconds.
- Verified behavior: reusable repository contract, compound uniqueness and duplicate mapping,
  `ObjectId` round trips, `update_one` with `$set`, deterministic sorting, and readiness ping.
- Authentication: passwordless service-account OIDC succeeded; no database password, access token,
  or service-account key was stored.

After the GCP run, record the date, region, PyMongo version, image tag, Terraform plan/apply result,
Cloud Run Job execution result, pass/fail totals, and sanitized errors. Do not record database UIDs,
tokens, or credentials.

## MongoDB Atlas fallback criteria

Choose MongoDB Atlas only if at least one of these remains true after reproducing the result on a
fresh dedicated Firestore spike database:

- A required repository-contract behavior is unsupported or observably incorrect.
- `ObjectId`, duplicate-key translation, `$set`, deterministic sorting, or readiness cannot be made
  reliable without a Firestore-specific repository fork.
- Required compound/unique indexes cannot be created and operated with a least-privilege deployment
  model.
- A documented Firestore limitation blocks the secure Cloud MVP and has no acceptable short-term
  workaround.
- Measured latency, availability, or cost for the MatrixedMind access pattern fails an explicitly
  recorded MVP acceptance threshold.

Do not fall back for a transient IAM, DNS, image, or tooling error. Record and fix setup blockers,
then rerun the same Cloud Run Job.

## References

- [Create and manage Firestore MongoDB-compatible databases](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/create-databases)
- [Authenticate and connect from Cloud Run](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/connect)
- [Manage MongoDB-compatible indexes](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/indexing)
- [Supported MongoDB 6.0 features](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/supported-features-60)
- [Behavior differences](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/behavior-differences)
