# Cloud MVP verification follow-up register

## Purpose and status

MatrixedMind's Milestones 0 through 12 delivered their planned implementation and documented
operational controls. This register is the single source of truth for Cloud MVP verification and
its remaining cleanup. Transferring an item here does **not** mark it verified.

Milestone 13, [Public project documentation](ROADMAP.md#milestone-13-public-project-documentation),
is the next product implementation milestone. The required items below do not block starting or
implementing Milestone 13. The validated restore clears the higher-sensitivity recovery blocker;
the isolated resources still require their separately approved destructive cleanup before Cloud
MVP closeout is complete.

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

**Status:** Isolated clone validation completed on 2026-08-13. Target access is removed and the
delete-protected clone is preserved pending separately approved cleanup.

**Blocks:** Only Cloud MVP closeout and temporary-resource hygiene until cleanup. Successful marker,
ping, and repository-contract validation clear this item's higher-sensitivity recovery blocker. It
does not block Milestone 13.

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
`READY`; PITR was not inherited. The first two target executions failed with intentionally
sanitized database-operation evidence and each exact target-conditioned `roles/datastore.user`
grant was removed immediately afterward.

The diagnostic image tagged `a0f4c35` then passed 27 focused tests locally and was published by
immutable digest. Its first live execution, `matrixedmind-closeout-target-q4sgm`, classified the
failure as `marker-read/authorization-failure`. The prior runs had allowed only 20 seconds for the
new conditional IAM grant, shorter than Firestore's documented IAM cache interval of up to five
minutes. The second bounded attempt restored the same database-specific grant without broadening
access, waited the full 300 seconds, and ran execution `matrixedmind-closeout-target-fvwcg`.
That execution completed successfully at `2026-08-13T00:29:38.223107Z`, proving the exact cloned
marker and payload, database ping, and Firestore repository-contract suite. The binding was removed
immediately and verified absent. Logs contained only the successful container exit, and no URI,
token, credential, repository-test output, or exception text was emitted.

The delete-protected clone, source marker, source and target jobs, and temporary identities remain
only for the separately approved cleanup. The normal development service, production, Terraform
state, and secret versions were not changed by validation. A fresh normal locked development plan
at `2026-08-13T00:38:08Z` reported zero managed or output changes. Its scope guard accepted only
refresh drift: IAM ETags from the temporary binding cycle, Firestore timing metadata, Artifact
Registry update time, and the workflow-owned Cloud Run image and deployment metadata.

### 4. Production Firestore composite-index readiness recheck (Milestone 12)

**Status:** Completed on 2026-08-13. All five production composite indexes are ready.

**Blocks:** Nothing. The production query-path readiness requirement is verified.

**Acceptance criteria:** Perform a bounded read-only production index-status check; confirm both
indexes are ready before relying on their query paths, or record their current state and the
operational response if either remains unavailable.

**Approval and evidence:** No mutation is authorized or needed for the status check. Record the
UTC check time, sanitized index identifiers or count, readiness result, and any follow-up decision.
See [OPERATIONS.md](OPERATIONS.md#cost-and-connectivity-review).

**Evidence:** A bounded read-only check of project `matrixedmind-prod` and database
`matrixedmind-prod` at `2026-08-13T00:32:14Z` reported five total MongoDB-compatible composite
indexes: five `READY`, zero `CREATING`, and zero in any other state. No production mutation was
performed.

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
