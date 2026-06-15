---
name: review-changes
description: Review the current diff in each affected submodule against the spec before opening PRs — checks every REQ-ID is implemented, tasks are done, and flags issues. Run after implementing, before /pr-from-plan.
argument-hint: "[--ticket <jira-ticket>]"
---

# shipkit · review-changes

Read `.shipkit/config.yml` and the spec for the ticket (or infer from the current branch name).

For **each affected submodule** (those with a feature branch / uncommitted changes):
```bash
git -C <path> status --short
git -C <path> diff <branch>...HEAD
```

Check the diff against the spec's `## Requirements` and `## Tasks`:
1. **Coverage** — every `REQ-NNN` has corresponding code; every checked task is actually done;
   flag unchecked tasks and uncovered requirements.
2. **Discipline** — FE keeps BFF routes proxy-only (no business logic); BE changes start from
   `api/api.yml`; voice changes stay staging-only.
3. **Correctness smells** — obvious bugs, missing error handling, missing tests, broken contracts.

For a deeper line-level pass, you may also invoke the repo's own `/code-review` if present.

Report per submodule: ✅ ready / ⚠️ issues (with file:line). Do **not** open PRs here —
that's `/pr-from-plan`. End by checking off completed tasks in `spec.md`.
