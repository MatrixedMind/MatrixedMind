---
name: matrixedmind-improve-process
description: Review completed MatrixedMind delivery evidence and recommend the smallest reusable process prevention. Use when the owner requests a post-milestone or post-PR process review, after repeated blockers or retries, when a coordinator process-event ledger is nonempty, or when recurring review themes or unresolved process debt remain.
---

# MatrixedMind Improve Process

## Establish a read-only evidence boundary

Identify the repository ref or worktree, completed or closing deliverable, commit or time range,
coordinator process-event ledger, review threads, validation results, task handoff, and owner notes
that are actually available. Read the matching roadmap acceptance criteria and relevant
instructions before judging the delivery.

Use only supplied or locally discoverable evidence: Git history and diffs, repository documents,
validation output, review artifacts, and task handoff. Do not infer missing history from a final
diff, claim that a condition was tested when evidence only documents it, access live systems, or
preserve raw logs or transcripts. State evidence gaps and their effect on confidence.

Use `matrixedmind_process_reviewer` only for this completed-delivery historical analysis. Keep
`matrixedmind_reviewer` responsible for correctness, regressions, maintainability, and missing test
coverage in a bounded code diff.

## Reconstruct and assess

1. Build a compact timeline of material decisions, failures, retries, escalations, reviews, and
   verification. Treat each coordinator ledger entry as a pointer to evidence, not a conclusion.
2. Classify each supported finding under one primary type: correctness defect; missing guardrail or
   test; unclear ownership or approval; tool, sandbox, authentication, or credential-layer
   confusion; model-routing failure; excessive retries, polling, replay, or context growth; scope
   drift; documentation disagreement; or unavoidable external blocker.
3. For each finding, distinguish fact from inference and give concise evidence, time/usage/risk
   impact, root cause, attempted remedy and outcome, the missed control, and the smallest prevention.
4. Call a theme recurring only when at least two findings share a root cause or concrete prior
   evidence establishes recurrence. Otherwise label it isolated and avoid new process machinery.
5. Say explicitly when evidence does not support a process change. Do not convert a one-off owner
   decision, missing external artifact, or unmeasured utilization concern into a reusable workflow.

## Select the smallest prevention

Recommend the narrowest effective surface:

1. Amend an existing skill, agent, or repository instruction.
2. Add a focused test or deterministic guard.
3. Create a new skill or agent only for a genuinely distinct repeated workflow.
4. Require manual owner intervention when automation would cross an authority or safety boundary.

Recommend changes only. Do not edit instructions, create agents, change permissions, run cloud
operations, publish changes, or mutate any external system.

## Promote a GitHub issue candidate cautiously

Add an issue candidate to the action register only when all of these are supported: concrete
evidence; meaningful correctness, security, time, or usage impact; reusable prevention; testable
acceptance criteria; and no equivalent existing issue. Perform a read-only duplicate search before
promotion. The read-only process reviewer uses a supplied local issue export or sanitized duplicate
search result. When current repository issue state is required, the coordinator may perform an
authorized read-only GitHub connector or API search and supply only the result; this does not grant
issue-write authority to either role. If no search result is available, keep the item as a local
recommendation with `duplicate search pending`; do not call it an issue candidate.

For every candidate, return:

- Title.
- Observed pattern.
- Evidence links or local refs.
- Recurrence count and confidence.
- Impact.
- Current workaround.
- Proposed surface.
- Acceptance criteria.
- Owner.
- Disposition.
- Validation required before closure.

Do not create an issue automatically. Issue creation is an external write requiring explicit owner
approval unless the owner later grants narrow standing authorization. Never include secrets,
tokens, sensitive logs, personal record content, or raw transcripts. Recommend closing an issue
only after the prevention is implemented and validated on a later representative task, not merely
when its implementation is merged.

## Return a decision-ready report

Return, in order:

1. **Scope and confidence** — evidence boundary, material gaps, and whether the deliverable met its
   documented acceptance criteria.
2. **Timeline** — only events that shaped outcome, time, usage, or risk.
3. **Findings** — evidence, impact, root cause, missed control, prevention, and isolated or recurring
   status, plus an explicit no-change statement for unsupported themes.
4. **Prioritized action register** — priority, owner, proposed surface, acceptance criteria,
   disposition (`adopt now`, `trial`, `defer`, or `reject`), and qualified issue candidates.
5. **Coordinator closeout evidence** — changed refs or commits, relevant acceptance criteria,
   validation and review state, unresolved blockers, evidence locations, next owner, and whether
   the process-improvement trigger is resolved.

Keep ordinary integration, validation, publication, and Copilot-review work with the coordinator.
