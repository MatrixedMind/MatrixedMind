# Cloud MVP

## Purpose

The Cloud MVP makes MatrixedMind privately usable over HTTPS and reachable from ChatGPT through a narrow write API. It is not a public launch, a polished collaboration product, or a broad automation platform.

The target path is:

```text
ChatGPT Custom GPT Action
        |
        | HTTPS + API key auth
        v
Cloud Run service
        |
        | app-level token validation
        v
/api/llm/* narrow write API
        |
        v
MatrixedMind repository layer
        |
        v
Firestore Enterprise edition with MongoDB compatibility
```

## Non-goals

- OAuth for the first ChatGPT integration.
- MCP or ChatGPT Apps SDK integration.
- Public publishing.
- Multi-user sharing UI.
- Import/export as a prerequisite for the first cloud MVP.
- Plugin infrastructure.
- Custom-domain activation before Milestone 11; the current hosted route remains unverified.
- Polished browser UI.
- Destructive LLM tools.
- Bulk import through the LLM API.

## Hosting

Use Cloud Run as the first HTTPS hosting target. Cloud Run may allow public unauthenticated invocation at the platform layer only because ChatGPT needs to reach the endpoint. MatrixedMind must still enforce app-level authentication and authorization for every sensitive route.

Public unauthenticated routes should stay limited to health/readiness and the LLM OpenAPI schema if the Custom GPT Action setup requires it.

Container images should be stored in Artifact Registry.

Runtime secrets must come from Secret Manager. Do not store real tokens, keys, passwords, or credentials in GitHub, docs, Terraform variables, `.env.example`, logs, or Codex output. The Firestore OIDC URI contains routing and authentication-mode configuration but no credential, so Terraform may inject it as a normal environment variable.

GitHub Actions should authenticate to GCP with Workload Identity Federation rather than long-lived service-account JSON keys.

## Persistence

Firestore Enterprise edition with MongoDB compatibility is the cloud persistence target because MatrixedMind already has a MongoDB-style repository adapter. The milestone 7 GCP job verified the repository contract and explicit compatibility checks against the dedicated development database.

Local development continues to use Docker Compose MongoDB. The local path should remain usable without GCP credentials for core work.

MongoDB Atlas remains the fallback only if Firestore MongoDB compatibility blocks the MVP.

## Firestore MongoDB Compatibility Spike

Before the cloud deployment baseline, run the repository contract suite against Firestore Enterprise MongoDB compatibility and document results.

The executable runbook and current result record live in
[`FIRESTORE_MONGO_SPIKE.md`](FIRESTORE_MONGO_SPIKE.md). The suite is opt-in and requires a dedicated
non-production database because it clears the target `records` collection.

The spike must verify at least:

- Connection settings required by the documented Firestore MongoDB-compatible connection string.
- Unique compound index behavior for `space` and `slug`.
- `ObjectId` handling.
- `DuplicateKeyError` behavior.
- `update_one` with `$set`.
- Sorting behavior.
- Readiness checks.
- Any required differences from local Docker Compose MongoDB.

Cloud Run uses its attached service account and PyMongo's GCP OIDC support. The documented
Firestore MongoDB-compatible connection string uses:

```text
loadBalanced=true
tls=true
retryWrites=false
authMechanism=MONGODB-OIDC
authMechanismProperties=ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE
```

Terraform derives the non-secret URI from the database UID, location, and ID. No Firestore password
or user credential is created or stored. SCRAM remains a diagnostic option outside the Cloud Run
runtime path.

## Cost Shape

Firestore Enterprise edition pricing measures reads and writes by document-size units, and index writes consume write units. Designs that grow unbounded embedded arrays inside a single document can increase read/write cost and operational risk.

The current MongoDB adapter stores revisions embedded in the record document. Before serious cloud use, revisions should move toward append-only documents:

```text
records
record_revisions
audit_events
llm_api_tokens
```

The intended cloud write path is:

```text
1. Update the current record document.
2. Insert an append-only revision document.
3. Insert an append-only audit event.
```

## LLM API Boundary

The first ChatGPT integration uses Custom GPT Actions with API key authentication. It does not use OAuth, MCP, or ChatGPT Apps SDK.

The LLM-facing API must be separate from the normal browser/internal API and must expose only narrow, scoped, non-destructive operations.

Initial endpoints:

```text
POST /api/llm/records/upsert
GET  /api/llm/records/{space}/{slug}
GET  /api/llm/records
```

Out of scope for the LLM MVP:

- Delete records.
- Publish records.
- Change visibility.
- Change indexing policy.
- Change sharing policy.
- Change authentication settings.
- Run admin actions.
- Bulk import data.

LLM-created records must default to private, draft, and noindex. Initial writes should be limited to an allowed space such as `llm-inbox`.

LLM writes must be attributed to a synthetic actor such as `llm:chatgpt`.

Every LLM write must create a revision and an audit event.

LLM API tokens must be:

- Scoped to allowed operations.
- Scoped to allowed spaces.
- Revocable.
- Hashed at rest.
- Limited by rate limits and body size limits.

## Manual Owner Setup Checklist

- Create or select a GCP project.
- Link billing to the project and confirm Terraform credentials can administer the project.
- Confirm the Service Usage API is available for the project so Terraform can enable the remaining APIs.
- Run the Terraform bootstrap root to create the versioned GCS state bucket, or create an equivalent state bucket manually.
- Run the Terraform dev environment root to enable required GCP APIs for Cloud Run, Artifact Registry, Secret Manager, IAM, Cloud Build or GitHub Actions deployment, Firestore Enterprise, and billing budgets.
- Use Terraform to configure Artifact Registry for MatrixedMind container images.
- Use Terraform to create Secret Manager entries for application secrets, then add secret versions manually without committing values. Firestore access does not use a stored secret.
- Use Terraform to configure GitHub Actions Workload Identity Federation.
- Use Terraform to create runtime and compatibility-test service accounts with Firestore data access.
- Use Terraform to create the Firestore Enterprise MongoDB-compatible database, or document the fallback to MongoDB Atlas.
- Use Terraform to create MongoDB-compatible indexes and the GCP compatibility-test job.
- Run the Firestore compatibility job in GCP and record its result.
- Use Terraform to configure Cloud Run service environment variables and secret mounts after the first image and secret versions exist.
- Confirm app-level auth is enforced before allowing public Cloud Run invocation.
- Use Terraform to configure billing budget alerts after billing is linked.

The Terraform roots and reusable modules currently support:

- `infra/terraform/bootstrap`: creates a private, versioned GCS state bucket.
- `infra/terraform/modules/*`: encapsulates Artifact Registry, runtime secrets, and the Cloud Run service.
- `infra/terraform/envs/dev`: enables required APIs; creates service accounts, Workload Identity Federation, a Firestore Enterprise database, and MongoDB-compatible indexes; composes the reusable modules; derives a passwordless GCP OIDC URI; and optionally creates the application service, compatibility-test job, and billing budget.
- `infra/terraform/envs/prod`: defines production application resources separately from the shared
  edge project. It stages Cloud Run privately and can create the production serverless NEG and
  global external managed backend service after activation prerequisites are approved.

The owner still must provide:

- The GCP project and billing link.
- Local or CI credentials allowed to run Terraform.
- Application secret values, added as Secret Manager versions outside Git. No Firestore password is required.
- The first pushed container image before enabling Cloud Run in Terraform.
- Application image and numbered runtime secret versions before enabling the Cloud Run application service.
- The decision to change the production `cloud_run_invocation_mode` from `private`, and only after
  app-level auth, the narrowly scoped public platform-invocation configuration, and the separate
  edge attachment are ready. In the hosted organization, Domain Restricted Sharing means this uses
  the Cloud Run Invoker IAM-check setting instead of an `allUsers` IAM binding.

After the owner applies the Cloud Run service configuration, `.github/workflows/deploy-dev.yml`
deploys only CI-verified `main` revisions. It uses Workload Identity Federation, pushes an immutable
commit-tagged image, updates only the service image, and verifies `/health` and `/ready` with an
authenticated identity token. Exact setup and recovery commands are in
[`OPERATIONS.md`](OPERATIONS.md).

The private development service was deployed and verified on 2026-07-28. Process health returned
the production environment, readiness successfully pinged Firestore MongoDB compatibility,
unauthenticated Cloud Run invocation returned `403`, and an authenticated request to a sensitive
browser route reached MatrixedMind's fail-closed production auth and returned `401`.

## ChatGPT Custom GPT Action Setup Checklist

- Expose the LLM-only OpenAPI schema at `/openapi-llm.json`.
- Create a scoped LLM token for ChatGPT and store only its hash in MatrixedMind.
- Configure the Custom GPT Action to use API key authentication.
- Restrict the action schema to the LLM endpoints only.
- Verify ChatGPT can create or update a private draft record in the allowed space.
- Verify ChatGPT can read only allowed records.
- Verify forbidden actions are not present in the schema and are rejected if attempted directly.
- Document token rotation and revocation steps.

The executable setup, test, rotation, and revocation procedure is in
[`CHATGPT_ACTION.md`](CHATGPT_ACTION.md).

## MVP Acceptance Criteria

The cloud MVP is done when:

1. MatrixedMind deploys to Cloud Run.
2. The app is reachable over HTTPS.
3. Runtime secrets are pulled from Secret Manager.
4. The app uses Firestore Enterprise MongoDB compatibility as the cloud database, or the roadmap explicitly falls back to MongoDB Atlas.
5. Browser routes require owner auth.
6. `/api/llm/*` requires a scoped LLM token.
7. ChatGPT can create or update a private draft record.
8. Every LLM write creates a revision.
9. Every LLM write records an audit event.
10. The LLM cannot delete, publish, change sharing, change indexing, change auth, or write outside its allowed space.
11. The LLM token can be revoked.
12. CI runs before deployment.
13. The README or deployment runbook explains the manual setup steps.
14. Billing budget alerts are configured.
