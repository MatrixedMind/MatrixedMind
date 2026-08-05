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

**Status:** Not executed.

**Blocks:** Full Milestone 8 CI verification and Cloud MVP verification closeout. It does not block
Milestone 13 or higher-sensitivity data use by itself.

**Acceptance criteria:** In an isolated disposable change or branch, deliberately cause one required
CI component (lint, type check, test, or Docker build) to fail; confirm `CI / Required` fails and
the pull request cannot satisfy the required status; remove the deliberate failure; then record the
failed run and the clean recovery run. Do not merge the deliberate-failure change.

**Approval and evidence:** A GitHub workflow/PR run is required. It is not a cloud mutation, but the
evidence must identify sanitized run URLs or identifiers, the intentionally failed component, the
required-check result, and the clean recovery result. See [TESTING.md](TESTING.md#ci-verification).

### 2. Non-production secret-rotation exercise (Milestone 12)

**Status:** Not executed.

**Blocks:** Higher-sensitivity data use and Cloud MVP verification closeout. It does not block
Milestone 13.

**Acceptance criteria:** Complete the development-only rotation procedure: create a new secret
version outside the repository, update only the matching explicit numeric Terraform version,
review and apply the plan, verify the new Cloud Run revision, run authenticated `/health` and
`/ready` checks plus one scoped non-production LLM request, and capture the rollback version before
any prior version is disabled.

**Approval and evidence:** Requires a separately approved audited cloud-mutation plan. Record the
environment, numeric versions (not values), revision identifier, sanitized endpoint and scoped
request results, rollback readiness, and whether the prior version was retained or disabled. See
[OPERATIONS.md](OPERATIONS.md#non-production-secret-rotation-test).

### 3. Isolated development restore exercise (Milestone 12)

**Status:** Not executed; the exact approval blocker was previously recorded.

**Blocks:** Higher-sensitivity data use, treating MatrixedMind as durable personal infrastructure,
and Cloud MVP verification closeout. It does not block Milestone 13.

**Acceptance criteria:** Restore approved test data from a recorded source timestamp into the
isolated development target, run repository-contract and readiness checks, preserve evidence, and
delete the temporary target only after the checks pass. On failure, stop access, preserve the
target for diagnosis, and leave the source database untouched.

**Approval and evidence:** Requires one separately approved audited live-mutation plan covering
the restore and cleanup. Record the source timestamp, target, test-data approval, check results,
cleanup result or retained-target reason, and rollback/containment outcome. See
[OPERATIONS.md](OPERATIONS.md#backup-and-recovery).

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
