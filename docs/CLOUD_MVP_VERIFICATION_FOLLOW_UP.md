# Cloud MVP verification follow-up register

## Purpose and status

MatrixedMind's Milestones 0 through 12 delivered their planned implementation and documented
operational controls. This register is the single source of truth for the remaining Cloud MVP
verification work that was intentionally not executed or remains conditional. Transferring an item
here does **not** mark it verified.

Milestone 13, [Public project documentation](ROADMAP.md#milestone-13-public-project-documentation),
is the next product implementation milestone. The required items below do not block starting or
implementing Milestone 13. They do constrain Cloud MVP closeout and the stated higher-sensitivity
or optional-feature uses until their own acceptance criteria are met.

Follow the detailed operational procedures in [OPERATIONS.md](OPERATIONS.md). Before any live cloud
mutation, use the [cloud mutation approval gate](OPERATIONS.md#cloud-mutation-approval-gate): present
one audited plan and wait for explicit approval. Record the date, environment, command or reviewed
plan identifier, sanitized result, and rollback outcome in the appropriate operational evidence
location; never record secret, token, or credential values.

## Required closeout work

### 1. Deliberate CI negative-path proof (Milestone 8)

**Status:** Completed on 2026-08-12.

**Blocks:** Nothing. The deliberate negative path and clean recovery are verified.

**Acceptance criteria:** In an isolated disposable change or branch, deliberately cause one required
CI component (lint, type check, test, or Docker build) to fail; confirm `CI / Required` fails and
the pull request cannot satisfy the required status; remove the deliberate failure; then record the
failed run and the clean recovery run. Do not merge the deliberate-failure change.

**Approval and evidence:** A GitHub workflow/PR run is required. It is not a cloud mutation, but the
evidence must identify sanitized run URLs or identifiers, the intentionally failed component, the
required-check result, and the clean recovery result. See [TESTING.md](TESTING.md#ci-verification).

**Evidence:** Disposable PR
[`#29`](https://github.com/MatrixedMind/MatrixedMind/pull/29) introduced only an intentional Ruff
failure and was closed without merge. Workflow run
[`31622297572`](https://github.com/MatrixedMind/MatrixedMind/actions/runs/31622297572) reported
`Python quality` and `CI / Required` as failed while Docker and Terraform passed; GitHub reported
the pull request as blocked. After the probe was removed on the same branch, workflow run
[`31622432621`](https://github.com/MatrixedMind/MatrixedMind/actions/runs/31622432621) reported the
Python, Docker, Terraform, and aggregate `CI / Required` checks as successful. The optional
credential-gated Firestore lane skipped in both runs as designed.

### 2. Non-production secret-rotation exercise (Milestone 12)

**Status:** Completed in development on 2026-08-12.

**Blocks:** Nothing. The development rotation requirement is verified.

**Acceptance criteria:** Complete the development-only rotation procedure: create a new secret
version outside the repository, update only the matching explicit numeric Terraform version,
review and apply the plan, verify the new Cloud Run revision, run authenticated `/health` and
`/ready` checks plus one scoped non-production LLM request, and capture the rollback version before
any prior version is disabled.

**Approval and evidence:** Requires a separately approved audited cloud-mutation plan. Record the
environment, numeric versions (not values), revision identifier, sanitized endpoint and scoped
request results, rollback readiness, and whether the prior version was retained or disabled. See
[OPERATIONS.md](OPERATIONS.md#non-production-secret-rotation-test).

**Evidence:** Secret `matrixedmind-dev-app-secret-key` version 2 is active on ready revision
`matrixedmind-dev-00013-br6`; rollback version 1 remains enabled. The first version-2 revision,
`matrixedmind-dev-00012-4cc`, exceeded its 512 MiB memory limit while `uv run` attempted a runtime
development-dependency sync and received no traffic. Commit `f69a78f` changed the production
container command to `uv run --no-sync`; the corrected amd64 image was deployed by immutable
digest, became ready, and serves 100% of development traffic. Authenticated `/health` and `/ready`
checks returned `200`, startup logs contained no dependency synchronization or memory-limit event,
and the fresh locked Terraform reconciliation plan reported zero managed changes. Cloud Run Job
execution `matrixedmind-closeout-source-h6t4h` then passed token save, metadata identity-token,
health, readiness, scoped LLM record access, exact token revocation, and post-revocation rejection.
No prior secret version was disabled.

### 3. Isolated development restore exercise (Milestone 12)

**Status:** Isolated clone completed on 2026-08-12, but target validation failed before the marker
and repository contract could be verified. Target access is removed and the clone is preserved.

**Blocks:** Higher-sensitivity data use, treating MatrixedMind as durable personal infrastructure,
and Cloud MVP verification closeout. It does not block Milestone 13.

**Acceptance criteria:** Restore approved test data from a recorded source timestamp into the
isolated development target, run repository-contract and readiness checks, preserve evidence, and
delete the temporary target only after the checks pass. On failure, stop access, preserve the
target for diagnosis, and leave the source database untouched.

**Approval and evidence:** Requires an approved audited creation-and-validation mutation plan.
After successful validation and current target rediscovery, destructive cleanup requires a second
exact plan and explicit approval; clone approval never implies deletion approval. Record the source
timestamp, target, test-data approval, check results, cleanup result or retained-target reason, and
rollback/containment outcome. See
[OPERATIONS.md](OPERATIONS.md#backup-and-recovery).

**Evidence:** Temporary source identity `mm-dev-closeout-source` is conditioned to database
`matrixedmind-spike`, and the pinned source job has invoker access only to `matrixedmind-dev`.
Execution `matrixedmind-closeout-source-8jdjt` seeded marker
`cloud-mvp-closeout-20260812` at `2026-08-12T21:17:13.802056Z`. The selected whole-minute source
timestamp is `2026-08-12T21:18:00Z`; at `2026-08-12T21:18:22Z` it was in the past, PITR was enabled,
and the source `earliestVersionTime` was `2026-08-05T21:19:00Z`. Clone operation
`h8Dhdvjun4hPSGKfMGUxhRAqMXRzZXctc3UIIgwQHho` completed successfully at
`2026-08-12T22:55:31.924744Z`, creating delete-protected target
`matrixedmind-dev-restore-validation-20260812-2118` from that exact snapshot. The target is
Enterprise, MongoDB-compatible, and all five cloned MongoDB-compatible composite indexes reported
`READY`; PITR was not inherited. Execution `matrixedmind-closeout-target-dxxdb` then exited 1 at
`2026-08-12T23:08:43.824392Z` with the intentionally sanitized blocker `database operation could
not be completed`, so neither the cloned marker nor the repository contract is verified. The exact
target-conditioned `roles/datastore.user` binding was removed. The delete-protected clone, target
job, and target service account are preserved without database access for diagnosis; the source
marker and source-only resources remain intact. No database deletion or other cleanup occurred.
An explicitly approved one-time diagnostic retry reconfirmed the completed clone, all five ready
indexes, exact private target URI, pinned image digest, job identity and arguments, and absent
target access. Google's native MongoDB-compatible `databases ping` did not return within 60 seconds
for either the target or the known-good source under the same operator environment, so it could
not distinguish clone readiness. No IAM denial for the validator was visible to the read-only
observer. After the exact conditional binding was restored, execution
`matrixedmind-closeout-target-th7hv` reproduced the same sanitized database-operation failure and
exited 1 at `2026-08-12T23:35:56.228796Z`. The binding was immediately removed again and verified
absent. No further retry or permission broadening is authorized; diagnosis now requires a reviewed
plan that can distinguish OIDC authorization, endpoint selection, and driver/server failures
without exposing the URI, token, or credential material.
The follow-up harness now emits only a fixed operation stage and fixed exception category, such as
`marker-read/authorization-failure` or `marker-read/server-selection-timeout`; it never renders the
underlying exception text. Unit tests cover every emitted category and explicit URI/token
non-disclosure. Repository-contract test output is discarded and represented only as
`repository-contract/test-failure`; client teardown cannot mask an earlier classified failure.
This repository change is not live evidence: a newly built immutable image, job
update, target-access regrant, and diagnostic execution still require a separate audited approval.

### 4. Production Firestore composite-index readiness recheck (Milestone 12)

**Status:** Pending read-only recheck. At the 2026-07-31 cost review, two of five production
composite indexes reported `CREATING` even though their associated operations reported complete.

**Blocks:** Reliance on the two affected production query paths and Cloud MVP verification closeout.
It does not block Milestone 13 or higher-sensitivity data use on its own.

**Acceptance criteria:** Perform a bounded read-only production index-status check; confirm both
indexes are ready before relying on their query paths, or record their current state and the
operational response if either remains unavailable.

**Approval and evidence:** No mutation is authorized or needed for the status check. Record the
UTC check time, sanitized index identifiers or count, readiness result, and any follow-up decision.
See [OPERATIONS.md](OPERATIONS.md#cost-and-connectivity-review).

## Conditional optional-feature work

### 5. ChatGPT-integration Action API IP allowlist validation (Milestone 11)

**Status:** Not applicable while the optional Action API allowlist remains disabled.

**Blocks:** Only activation of the optional Cloud Armor Enterprise IP-allowlist feature. It does not
block Milestone 13, Cloud MVP closeout, or higher-sensitivity data use; scoped bearer-token
authentication remains mandatory regardless of network policy.

**Activation and acceptance criteria:** First decide to opt in, review Cloud Armor Enterprise cost,
the current published ChatGPT-integration range feed, and its refresh process, then supply a
reviewed address group. After the allowlist is enabled, verify that a current ChatGPT integration
request is accepted and an unapproved source is denied without weakening application-level bearer
authentication.

**Approval and evidence:** Enabling or changing the policy requires a separately approved audited
cloud-mutation plan. Record the reviewed range-source version or date, policy revision, sanitized
approved and denied request results, refresh owner/process, and rollback plan. See
[OPERATIONS.md](OPERATIONS.md#terraform).

## Completion rule

Required closeout work is complete only when all four required items have recorded evidence meeting
their acceptance criteria. Conditional item 5 remains not applicable unless an operator elects to
enable that feature; if enabled, it must be completed before the feature is relied upon.
