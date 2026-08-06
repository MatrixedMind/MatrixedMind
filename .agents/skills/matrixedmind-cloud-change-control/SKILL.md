---
name: matrixedmind-cloud-change-control
description: Audit and gate MatrixedMind Terraform and GCP changes before planning or mutation. Use for Terraform plan or apply review, GCP IAM or resource mutation review, drift reconciliation, imports, moved state, identity transitions, recovery exercises, secret rotation, and any operation that could affect Terraform state, Cloud Run, IAM, secrets, databases, budgets, alerts, shared edge infrastructure, or deployments.
---

# MatrixedMind Cloud Change Control

## Establish the change record

Stop until the record contains every item below. Discover routine identifiers read-only instead of
asking the owner to invent them.

- Environment and confirmed GCP project ID.
- Exact Terraform root and expected versioned GCS backend bucket and prefix.
- Interactive operator identity, active gcloud configuration, ADC principal, Terraform provider
  identity, backend identity, and every service-account impersonation hop.
- Mutation objective, intended resource addresses, action per address, and explicitly excluded
  projects or systems.
- Owner decisions for IAM or security boundaries, notification destinations, spending limits,
  data-safety or recovery actions, destructive actions, and other live mutations.

Read `AGENTS.md`, `docs/OPERATIONS.md`, `docs/TESTING.md`, the applicable roadmap section, and
relevant ADRs before continuing. For secret rotation or recovery, also read
`docs/CLOUD_MVP_VERIFICATION_FOLLOW_UP.md`. Treat repository documentation as intended controls;
verify current deployed state separately with bounded read-only discovery.

Classify failures independently: sandbox or network denial, local credential retrieval, remote
authentication, authorization, Git transport, Terraform backend/state/lock access, and provider or
impersonated identity. Do not use success in one layer as evidence for another.

## Pass six distinct gates

### 1. Read-only discovery

Verify the project parent, active operator, ADC, provider configuration, impersonation chain,
backend bucket/prefix, state lineage and serial when available, relevant IAM, and current resource
state. Redact secret values, token-like data, state contents, billing identifiers, and personal
notification destinations from reports.

Stop on any identity, project, root, backend, or scope mismatch. A local account switch does not
transfer project ownership or prove provider, backend, IAM, or state access. Do not revoke legacy
access until replacement authority, state access, and rollback have been proven.

### 2. Plan generation

Generate a saved plan only after the discovery record is complete. Use the intended initialized
root and its normal remote backend with locking enabled. Keep plan artifacts outside the repository
with restrictive local permissions because both binary plans and JSON can contain sensitive values.
Review the Terraform diff, module sources, `.terraform.lock.hcl`, provider selections and
checksums, and any external data sources or local execution before running Terraform. Planning loads
provider code and can execute configured plan-time data sources; do not run an untrusted change.
Do not combine this audit with `terraform init -upgrade` or an unreviewed provider/module upgrade.

Never use `-lock=false`, `-backend=false`, an alternate or copied state, manual state JSON edits, or
a backend-free substitute for a live plan. Do not use targeted planning to hide unrelated changes;
use `-target` only for an explicitly documented recovery exception approved as part of the scope.
Never parse human-readable plan text.

Create a private plan-artifact directory and JSON only from the saved plan. Set `umask 077` before
creating it, keep the binary plan, JSON plan, and scope file in that directory, and set each file to
mode `0600`. Verify the modes with the platform's `stat` command before scope review or apply.

```sh
umask 077
plan_dir="$(mktemp -d "${TMPDIR:-/tmp}/matrixedmind-tf-plan.XXXXXX")"
touch "$plan_dir/scope.json"
terraform -chdir=<root> plan -lock=true -input=false -out="$plan_dir/plan.bin"
terraform -chdir=<root> show -json "$plan_dir/plan.bin" > "$plan_dir/plan.json"
chmod 600 "$plan_dir/plan.bin" "$plan_dir/plan.json" "$plan_dir/scope.json"
```

Populate `scope.json` without replacing its inode. On macOS verify each file with `stat -f '%Lp'`;
on Linux use `stat -c '%a'`; every result must be `600`. Stop if private creation or mode
verification fails. When the plan is rejected, superseded, applied and verified, or no longer needed
for an approved diagnostic record, remove only that resolved private directory and confirm it is
gone. Never retain plan artifacts in the repository or a shared temporary path.

### 3. Plan-scope audit and approval

Inspect the JSON and classify every managed change and root output change. Resource actions are
`create`, `update`, `delete`, `replace`, `import`, or `state-move`; output actions are `create`,
`update`, `delete`, or `replace`. Treat deletes, replacements, and output sensitivity downgrades as
destructive. Flag all unexpected changes, especially Cloud Run, IAM, secrets, databases, budgets,
alerts, shared edge, deployment resources, output unknowns, and outputs exposing sensitive values.
Imports and state moves require exact source and destination review; never edit or copy state
manually.

Use `.codex/scripts/terraform-plan-scope-guard` for deterministic scope enforcement. Give it a JSON
scope file with one exact entry per expected changed address:

```json
{
  "scope_version": 1,
  "allowed_changes": [
    {
      "address": "module.example.google_example_resource.this",
      "actions": ["update"],
      "allow_unknown": false,
      "allow_sensitive": false
    }
  ],
  "allowed_drift": [],
  "allowed_outputs": []
}
```

For an import, include both `"import"` and its Terraform action, normally `"create"`. For a moved
resource, include `"state-move"`, any simultaneous Terraform action, and the exact
`"previous_address"`. Set `allow_unknown` or `allow_sensitive` only for an individually reviewed
address and record why exact values cannot be known or shown.

For an output change, add one exact `allowed_outputs` entry with `name`, `actions`,
`allow_unknown`, `allow_sensitive`, and `allow_sensitive_downgrade`. Default every allow flag to
false. Approve a sensitive downgrade only when the owner explicitly intends the output to become
plaintext and the resulting exposure has been reviewed.

Use declarative `import` and `moved` blocks so the saved plan exposes the operation. Legacy
`terraform import`, `terraform state mv`, `terraform state rm`, `terraform state push`, backend
migration, and similar commands mutate state outside the guard's resource-change contract. Do not
run them as a shortcut. If declarative planning cannot represent an exceptional recovery, stop and
present that limitation plus a separate state-recovery plan with exact commands, normal locking,
versioned-backend recovery, verification, and explicit owner approval.

```text
python .codex/scripts/terraform-plan-scope-guard \
  <saved-plan.json> --scope <scope.json>
```

The guard must pass before approval, but passing is not approval. Hash the saved binary plan and
bind the audited mutation plan to that digest. If the plan is regenerated, identity changes, state
serial changes, or scope changes, discard the approval and repeat this gate.

Present one concise audited mutation plan containing:

1. Objective, environment, confirmed project, Terraform root, backend, and plan digest.
2. Operator, gcloud, ADC, provider, backend, and impersonation identities.
3. Exact allowed resource addresses and classified actions; explicitly state whether creates,
   deletes, replacements, imports, state moves, drift, output changes, sensitivity downgrades,
   sensitive markers, or unknown values exist.
4. Excluded systems and any unexpected high-risk resource class found by the guard.
5. Risks, blast radius, secret-handling constraints, and owner decisions.
6. Exact apply command using the reviewed saved plan, verification, rollback or containment, and
   stop conditions.

Stop and wait for explicit owner approval of that exact plan. Do not infer approval from earlier
work, repository edits, read-only discovery, a prior plan, or a general instruction to continue.

### 4. Apply

Immediately before apply, recheck the operator, project, provider/impersonation identities, backend,
lock availability, saved-plan digest, and approval scope. Apply only the approved saved plan. Stop
on stale state, identity drift, lock contention, unexpected prompting, or a changed artifact. Never
expose secret values and never disable locking.

### 5. Verification

Verify only the approved objective and its documented security, health, readiness, IAM, alert,
budget, secret-version-number, database, or routing checks. Record sanitized identifiers and
results. Run a fresh normal locked plan to detect remaining drift; it requires a new approval before
any further apply.

### 6. Rollback or containment

Use the audited rollback path. Roll back configuration through another reviewed Terraform plan,
not console edits. For failed recovery validation, preserve the isolated target for diagnosis and
leave the source untouched. For secret rotation, retain the prior numeric version until the new
revision verifies; never record the value. Destructive cleanup is a separate approved mutation.

## Guard limitations

The scope guard checks Terraform plan JSON offline. It does not prove which backend was used,
whether locking was enabled, current GCP or provider identity, the safety of provider behavior,
plan-time external-program side effects, actual API-side effects, check-block outcomes, policy
inheritance, changes after plan creation, or the value of unknown attributes. It compares resource
addresses, resource and root-output action vectors, drift declarations, output sensitivity
downgrades, and sensitive or unknown markers; it deliberately does not print values. Terraform JSON
can contain plaintext sensitive data despite markers, so
protect and delete artifacts according to the audited procedure. Unsupported format majors,
deferred changes, malformed change structures, deposed instances, and unapproved sensitive or
unknown markers fail closed. Backend migration and imperative state commands are not represented
by `resource_changes` and therefore cannot be approved by the guard.
