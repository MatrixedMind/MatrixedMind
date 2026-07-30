---
name: matrixedmind-copilot-review-loop
description: Run the bounded post-push GitHub Copilot review loop for a MatrixedMind pull request. Use when a pushed MatrixedMind PR awaits Copilot review, when Copilot feedback must be addressed, or when completing the post-push phase of a milestone PR.
---

# MatrixedMind Copilot Review Loop

## Resolve and wait

1. Verify the PR is ready for review and non-draft before beginning the loop. If an existing
   milestone PR is a draft, mark it ready under the milestone publication standing authorization;
   otherwise stop with an exact blocker.
2. Resolve the repository, PR number and URL, current head SHA, and Copilot review configuration. Determine whether automatic Copilot review includes new pushes.
3. Before treating thread-aware `gh` or GraphQL failures as authentication or authorization,
   inspect the effective sandbox and network restrictions. Treat restricted-sandbox results as
   inconclusive; use at most one narrowly elevated network-capable verification before declaring
   a blocker, without printing credentials.
4. Use event-driven or non-model waiting where available. Do not spend repeated model turns polling unchanged GitHub state; if polling is unavoidable, use a coarse cadence and retrieve only deltas.
5. Stop with an exact blocker if authentication or required permissions fail, Copilot is not configured, the PR closes or merges, or a bounded timeout expires. If the same external-state failure recurs after one verified retry, stop with evidence and the next action rather than polling, broad web searches, repeated login instructions, or additional model turns.

## Read and classify feedback

- Use the installed `github:gh-address-comments` workflow when available; otherwise use an equivalent thread-aware GitHub GraphQL query. Retrieve unresolved and outdated state, file and line anchors, surrounding diff context, author, timestamps, and associated commit when available. Do not treat flat top-level comments as complete thread state.
- Classify every Copilot comment as legitimate and actionable, legitimate but explanation-only, already addressed or outdated, duplicate, ambiguous or requiring a product decision, or incorrect or inapplicable.
- Before changing code, inspect the implementation, tests, documentation, and surrounding diff. Verify dependency or provider claims against locked versions and authoritative documentation; reject speculative style-only feedback without material impact; identify conflicts with roadmap decisions, ADRs, security invariants, and other comments.

## Address only legitimate findings

1. Group legitimate findings by root cause or affected behavior. Keep every change traceable to a legitimate finding or cluster.
2. Use `matrixedmind_worker` for bounded implementation, `matrixedmind_reviewer` for ambiguous correctness questions, and `matrixedmind_security_reviewer` for authentication, authorization, IAM, secrets, isolation, migration, or exposure concerns.
3. Run focused verification for each cluster and then the relevant repository quality gates. Push verified fixes to the existing PR branch.
4. Do not reply to comments, resolve threads, dismiss reviews, merge, or close the PR without explicit authorization.

## Re-review deliberately

1. Record the new head SHA after each fix push. Await automatic review for that head; otherwise request one Copilot re-review only when supported and authorized.
2. Do not treat a review of an older SHA as final evidence for the new head. Do not reprocess outdated, duplicate, repeated, or already-addressed comments.
3. Repeat until no unresolved legitimate actionable findings remain on the current head, relevant verification passes, or a stop condition occurs. Allow at most three fix-and-re-review cycles by default, then report remaining findings.

## Capture supported learnings and hand off

- Examine only legitimate findings. Identify a theme only when at least two share a current-PR root cause or concrete prior evidence shows recurrence. Do not generalize from one isolated or rejected comment.
- For each supported theme, record the issue pattern, representative files or behavior, underlying cause, why existing controls missed it, and the smallest practical prevention. Recommend, but do not automatically implement, regression or contract tests, checks, safer abstractions, focused instructions, checklists, skills, or clearer architecture/provider-version documentation.
- Return the review-cycle count, final reviewed head SHA, addressed legitimate findings, rejected/duplicate/outdated/ambiguous comments, commits or change clusters, verification results, unresolved blockers, automatic-new-push-review availability, and a Review learnings section or an explicit statement that no recurring legitimate theme was found.
- Keep raw review payloads and large comment dumps out of coordinator context. Do not use Browser or GUI control, retain the existing two-subagent and one-level-delegation limits, close completed subagent threads, and do not create a separate PR-shepherd agent.
