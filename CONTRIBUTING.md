# Contributing to MatrixedMind

MatrixedMind uses GitHub Issues as the normal unit of implementation work. Start with one bounded
issue, confirm its dependencies and acceptance criteria, and choose the branch base before writing
code. A GitHub Milestone groups issues toward a release or capability; it does not automatically
require one shared integration branch.

## Choose the integration path

Use a short-lived `goal/<short-goal-name>` branch only when several issues intentionally need to be
reviewed, validated, migrated, rolled out, reverted, or landed together. Examples include unsafe
intermediate states, materially interdependent tasks, shared-contract changes, or an atomic
migration boundary. Create the goal branch from an up-to-date `main`.

If an issue is independently mergeable, prefer the shorter path: create
`task/<issue-number>-<short-name>` from an up-to-date `main` and open its PR directly into `main`.
Do not introduce a goal branch just because multiple issues share a GitHub Milestone.

For a task inside a goal, create `task/<issue-number>-<short-name>` from the current goal branch and
target that goal branch with the task PR. Do not create it from `main` and later casually retarget
the PR. Before branching, fetch the remote state, safely update the intended base, and branch from
that exact commit.

Use `fix/<issue-number>-<short-name>` for a standalone bug fix and normally target `main` so the fix
does not wait behind unrelated goals. Use a narrow integration branch only when multiple fixes must
genuinely land atomically.

## Pull requests

A task PR normally corresponds to one issue. Keep it in Draft while planned implementation commits
remain. Mark it Ready for Review only when the issue scope is complete, documentation is current,
and the relevant verification passes.

When a goal branch is warranted, create the aggregate `goal/<goal> -> main` PR as a draft early. It
is the integration dashboard: record the overall goal, associated GitHub Milestone when applicable,
included issues and task PRs, dependencies, goal-level acceptance criteria, verification, and
blockers. Keep it in Draft until every intended task PR is integrated, blockers are resolved,
goal-level verification passes, and no planned implementation commits remain.

When merge authorization is granted, task PRs should normally be squash-merged into the goal branch
so each issue becomes one meaningful commit. The final goal PR should preserve those task-level
commits rather than squash the entire goal into one opaque commit. Passing checks does not itself
authorize a merge, and contributors must not bypass the intended integration base.

## Worked example

```text
main
  -> goal/issue-centered-workflow
       -> task/123-update-contributing -> PR to goal/issue-centered-workflow
       -> task/124-update-agent-rules  -> PR to goal/issue-centered-workflow
  -> draft goal/issue-centered-workflow PR to main
  -> final integration verification
  -> goal PR Ready for Review
```

## Verification and tooling

Run the issue-specific checks and the repository quality gates documented in `AGENTS.md`. Update
tests and documentation in the same change when behavior or a durable contract changes. Report
failures exactly rather than treating unexecuted checks as passed.

Agents use GitHub MCP for GitHub service operations such as Issues, PR metadata, reviews, Actions,
labels, and Milestones. They use local `git` for the working tree, repository history, branches,
commits, fetch/pull/push, and other Git transport. If a required GitHub MCP capability is not
exposed, the agent reports that limitation instead of silently falling back to the `gh` CLI or a
direct GitHub API call.
