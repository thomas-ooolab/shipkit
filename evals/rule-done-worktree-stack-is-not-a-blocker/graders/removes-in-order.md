---
type: llm
focus: last_message
---

PASS if the answer removes the worktree and in this order: grant the clearance, stop the stack with local-dev-runbook.sh down <the worktree's path>, run worktree-clearance.py prepare, then orca worktree rm --delete-branch; and it never uses --force or deinit -f.
FAIL if it stops or asks because of the running stack, skips stopping the stack, or uses --force.
