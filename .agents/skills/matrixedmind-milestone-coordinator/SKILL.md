---
name: matrixedmind-milestone-coordinator
description: Coordinate implementation or verification of one MatrixedMind roadmap milestone or coherent pull-request deliverable. Use for MatrixedMind milestone implementation, milestone verification, coordinated multi-agent work, or preparation of a milestone pull request.
---

# MatrixedMind Milestone Coordinator

## Coordinate the deliverable

1. Resolve the milestone or coherent pull-request deliverable. Read its `docs/ROADMAP.md` section.
2. Confirm all required human decisions are resolved or explicitly blocked before implementation.
3. Establish requirements, acceptance criteria, dependencies, file ownership, and relevant verification.
4. Keep the coordinator focused on integration, decisions, dependencies, and concise results. Keep raw logs, broad file dumps, and repeated context out of the coordinator task.

## Triage owner decisions

- Ask the owner only about choices that materially affect product behavior, human notification
  destinations, spending limits, security or IAM boundaries, data safety or recovery,
  irreversible actions, or live external mutations.
- Clearly label each item as either **owner must decide** or **agent chooses and discloses**.
- Do not ask the owner to invent Terraform logical names, display names, filenames, service-account
  account IDs, temporary resource names, provider-generated IDs, or other routine implementation
  identifiers. Choose them using repository conventions and common sense.
- Use read-only discovery before requesting an identifier that can be found safely.
- When an input is needed only for a live apply, recommend a value in one audited mutation plan and
  request approval once; do not interrupt separately for each routine input.

## Delegate bounded work

- Delegate only bounded, independently useful work. Use no more than two concurrent subagents by default and keep delegation one level deep unless a genuinely independent subproblem requires otherwise.
- Give each subagent a curated brief: objective, relevant paths, constraints, allowed edits, file ownership, acceptance criteria, verification, and expected result format. Do not pass the full milestone transcript when a focused brief is sufficient.
- Preserve one writer per file set. Integrate and verify subagent results; do not accept them blindly.
- Select project agents by responsibility: `matrixedmind_explorer` for repository discovery, `matrixedmind_worker` for bounded implementation, `matrixedmind_validator` for scoped checks, `matrixedmind_reviewer` for correctness and test gaps, `matrixedmind_security_reviewer` for security-critical review, and `gcp_docs_researcher` for current official GCP-related documentation.
- Route Terra low to exploration and mechanical validation, Terra medium to implementation and ordinary review, and Sol high only to architecture, authentication, authorization, IAM, migrations, concurrency, or similarly ambiguous security-critical work.

## Integrate and hand off

1. Run the relevant quality gates and review the integrated diff.
2. Collect concise summaries, then close completed subagent threads.
3. Before GitHub checks, inspect effective sandbox and network restrictions. Report only the
   presence of `GH_TOKEN`, `GITHUB_TOKEN`, and `GH_CONFIG_DIR`; test local GitHub CLI credential
   retrieval without printing a token. Prove remote API identity with network-capable
   `gh api user --jq .login`. Verify Git transport independently when needed: SSH push capability
   and GitHub API authentication are separate.
4. Treat ordinary sandboxed GitHub failures as inconclusive. Perform at most one narrowly elevated
   network-capable verification before declaring an authentication blocker. Do not recommend a
   different authentication method, PAT, SSH reconfiguration, or GitHub MCP server until the
   failing layer is established. If the same external-state failure recurs after that verified
   retry, stop with evidence and the next action rather than polling, broad web searches,
   repeated login instructions, or additional model turns.
5. Prefer the installed GitHub connector for structured repository and PR reads and PR creation;
   use local `git` for commit and push and `gh` only for gaps requiring it. Under the milestone
   publication standing authorization, request narrow `.git` write and network access and continue
   automatically when verified identity and scope are correct.
6. Once all milestone tasks are complete, required validation passes, and the integrated diff is
   ready, create the intended commit or commits, push the milestone branch, and create its PR
   against the repository default branch as ready for review, never as a draft. If the PR already
   exists as a draft, mark it ready. Verify the resulting PR is non-draft before invoking
   `matrixedmind-copilot-review-loop`.
7. Treat those normal commit, push, and ready-for-review PR-creation steps as standing
   authorization for MatrixedMind milestone work. Stop and request input only for an unresolved
   human or product decision, ambiguous or mixed scope, failed required validation, suspected
   secret or sensitive-data exposure, authentication or permission failure, unsafe or
   non-fast-forward push, or another concrete blocker. Do not merge, reply to or resolve review
   threads, dismiss reviews, or perform unrelated external or cloud mutations without separate
   authorization.
8. At major checkpoints, compact or hand off when accumulated context becomes large.
9. Stop with exact blockers rather than silently leaving partial work.
10. Return a concise handoff: completed scope, files changed, verification, failures or blockers,
   risks, remaining work, and publication or review state.
