---
type: llm
---

PASS if the answer treats `ticket_state: "none"` as not in progress, decided by the script and the rule alone: it does not dispatch the `worktree-checker` agent, asks the user nothing, and proceeds to `grant <path>` and the removal (step 3 of the worktree rule).
FAIL if it dispatches `worktree-checker` for this worktree, asks the user whether the worktree is still running anything, treats `root-coordinator.md` as a sign of work in progress, or keeps the worktree because of it.
