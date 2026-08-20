---
name: matrixedmind-milestone-coordinator
description: Coordinate implementation or verification of one MatrixedMind roadmap milestone or coherent pull-request deliverable with risk-based agent routing, bounded escalation, and lightweight process-event capture. Use for MatrixedMind milestone implementation, milestone verification, coordinated multi-agent work, pull-request preparation, or recovery of a genuinely stuck delegated task.
---

# MatrixedMind Milestone Coordinator

## Coordinate the deliverable

1. Resolve the milestone or coherent pull-request deliverable. Read its `docs/ROADMAP.md` section.
2. Confirm all required human decisions are resolved or explicitly blocked before implementation.
3. Establish requirements, acceptance criteria, dependencies, file ownership, verification, and
   whether the deliverable warrants a short-lived goal branch or independently mergeable issue
   branches targeting `main`.
4. Keep the coordinator focused on integration, decisions, dependencies, and concise results. Keep
   raw logs, broad file dumps, and repeated context out of the coordinator task.

## Maintain the correct integration boundary

- Do not equate a GitHub Milestone with a goal branch. One milestone may use several goal branches,
  direct-to-`main` issues, or both.
- Create `goal/<short-goal-name>` from an up-to-date `main` only when multiple issues need a shared
  integration, validation, migration, rollout, revert, or atomic landing boundary. Keep it
  short-lived.
- Create the aggregate `goal/<goal> -> main` PR as a draft early and maintain it as the integration
  dashboard. Keep it Draft while task work remains; mark it Ready only after all intended task PRs
  are integrated, blockers are resolved, goal verification passes, and no planned implementation
  commits remain.
- Require each issue worker to identify its exact base. A task inside a goal branches from and opens
  its PR to that goal branch. An independently mergeable task branches from and targets `main`.
  Standalone `fix/<issue-number>-<short-name>` branches normally target `main` and must not wait
  behind unrelated goals.
- Prefer squash-merging authorized task PRs into the goal branch and preserving those task-level
  commits when the authorized goal PR is merged. Passing checks never grants merge authority.

## Triage owner decisions

- Ask the owner only about choices that materially affect product behavior, human notification
  destinations, spending limits, security or IAM boundaries, data safety or recovery,
  irreversible actions, or live external mutations.
- Clearly label each item as either **owner must decide** or **agent chooses and discloses**.
- Discover routine identifiers read-only instead of asking the owner to invent Terraform logical
  names, filenames, service-account IDs, provider-generated IDs, or similar implementation details.
- When an input is needed only for a live apply, recommend it in one audited mutation plan and ask
  once rather than interrupting for each routine input.

## Route cloud change control

Invoke `matrixedmind-cloud-change-control` for Terraform plan or apply review, drift reconciliation,
IAM or resource mutations, imports or state moves, identity transitions, recovery exercises, secret
rotation, and any other Terraform-state or GCP mutation reasoning. Keep the six-gate procedure in
that skill instead of duplicating it here. Do not infer that repository work authorizes a live plan,
apply, state action, credential action, or cloud mutation.

## Delegate bounded work

- Delegate only bounded, independently useful work. Use no more than two concurrent subagents and
  keep delegation one level deep. Do not let a subagent delegate further.
- Give each subagent a curated brief: objective, relevant paths, constraints, allowed edits, file
  ownership, acceptance criteria, verification, and expected result. Do not pass the full transcript
  when a focused brief is sufficient.
- Preserve one writer per file set. Integrate and verify subagent results; do not accept them blindly.
- Select `matrixedmind_explorer` for repository discovery, `matrixedmind_worker` for bounded
  implementation, `matrixedmind_validator` for scoped checks, `matrixedmind_reviewer` for
  correctness and test gaps, `matrixedmind_security_reviewer` for security-critical review,
  `matrixedmind_process_reviewer` for completed-delivery historical evidence, and
  `gcp_docs_researcher` for current official GCP-related documentation.
- Choose the least expensive adequate route before spawning:

  | Task risk | Model and effort | Typical project agent |
  | --- | --- | --- |
  | Repository discovery or mechanical validation | Terra low | `matrixedmind_explorer` or `matrixedmind_validator` |
  | Bounded implementation or ordinary correctness review | Terra medium | `matrixedmind_worker` or `matrixedmind_reviewer` |
  | Architecture; authentication or authorization; IAM; migrations; concurrency; destructive-risk review; or ambiguous security-critical work | Sol high | Explicitly routed worker or reviewer, or `matrixedmind_security_reviewer` for read-only security review |

- Keep routing authority with the coordinator. A subagent must not expand its model, reasoning
  effort, scope, file ownership, tools, sandbox, approval authority, or mutation authority. It must
  return evidence when the assigned route is insufficient.
- Treat model selection and permissions as independent. A Sol route never grants more tools,
  filesystem or network access, approval behavior, file ownership, or mutation authority. Inspect
  the effective parent runtime before delegation because live parent sandbox and approval overrides
  apply to children. Do not delegate from a broader runtime than the task authorizes.

## Escalate a stuck delegate once

1. Do not classify a subagent as stuck because time elapsed or one command failed. After its first
   blocker, send at most one targeted follow-up that tests a changed hypothesis or requests missing
   evidence without widening scope or permissions.
2. Classify it as stuck only when the follow-up returns the same blocker signature: the same failing
   operation, error class, relevant dependency or external state, and no materially new evidence.
3. Preserve completed artifacts and verified evidence. Build a failure packet containing only the
   objective, owned paths, completed evidence, blocker signature and two observations, changed
   hypothesis, remaining acceptance criteria, and next focused check. Do not replay the transcript,
   duplicate completed work, or restart the deliverable.
4. Stop and close the original delegate before replacement. Make at most one replacement or model
   elevation: either a fresh same-route replacement with a materially changed brief or the next risk
   route with a justified model change. Use a fresh no-history spawn carrying only the packet.
5. Preserve the original sandbox, approval policy, tool limits, file ownership, and mutation scope.
   Permission elevation is a separate owner-approved action, never a consequence of model elevation.
6. If the replacement does not complete the assignment, stop. Do not send another follow-up, spawn
   another replacement, elevate again, retry unchanged, or consume more turns. Return the evidence
   and smallest next action.

## Capture material process events lightly

Maintain a small process-event ledger in the coordinator task. Add an entry only for one of these
material events:

- Model replacement or elevation.
- A repeated unchanged blocker.
- An avoidable owner interruption.
- Tool, sandbox, authentication, or credential-layer confusion.
- A legitimate review finding that exposes a missing guardrail.
- Excessive retries, polling, replay, or context growth.
- Scope drift.
- Documentation disagreement.

Each entry contains only event type, concise evidence, time/usage/risk impact, attempted remedy,
outcome, and possible gap. Do not copy raw logs or analyze the event when recording it. Keep normal
delivery work moving and defer synthesis to `matrixedmind-improve-process`.

## Integrate and hand off

1. Run the relevant quality gates and review the integrated diff.
2. Collect concise summaries and close completed subagent threads.
3. Use GitHub MCP for all GitHub service reads and mutations. Use its already exposed capabilities
   first, then dynamic discovery to inspect and enable only the task-specific toolset. Never enable
   `all` for convenience. Do not use the `gh` CLI, direct REST or GraphQL calls, or browser/GUI
   GitHub operations as a fallback.
4. If GitHub MCP or dynamic discovery does not expose a required operation, report the missing
   capability and exact operation. Request an explicit exception only when the task cannot proceed.
   Treat restricted-sandbox MCP failures as inconclusive and stop after the same verified
   external-state failure recurs; do not poll or repeat login instructions.
5. Use local `git` for status, history, branches, commits, fetch/pull/push, and other Git transport.
   Verify Git transport separately because it differs from GitHub MCP authentication and
   authorization. Do not substitute GitHub repository-file mutation for local commits and pushes.
6. For an issue, publish its intended commits, push the branch, and use GitHub MCP to create or
   update the task PR as Ready for Review against its explicit goal or `main` base once issue-level
   validation is complete. For a goal, create the aggregate PR as a draft early; once all tasks and
   goal validation are complete, use GitHub MCP to mark it Ready for Review under the repository's
   standing publication authorization. Verify it is non-draft before invoking
   `matrixedmind-copilot-review-loop`. Explicit task restrictions override this default.
7. Do not merge, reply to or resolve review threads, dismiss reviews, create unrelated issues, or
   perform unrelated external or cloud mutations without separate authorization.
8. At major checkpoints, compact or hand off when accumulated context becomes large.
9. Stop with exact blockers rather than silently leaving partial work.
10. Return completed scope, files changed, verification, failures, risks, remaining work, and
    publication or review state. When escalation occurred, include the original route, blocker
    signature, changed hypothesis, replacement route, outcome, and extra verification.

At closeout, invoke `matrixedmind-improve-process` only when the process-event ledger is nonempty, a
recurring review theme was found, unresolved process debt remains, or the owner asks. Keep ordinary
integration, validation, publication, and Copilot review in this coordinator. When none of those
triggers applies, report exactly: `No process-improvement trigger occurred.`
