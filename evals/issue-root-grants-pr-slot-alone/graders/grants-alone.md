---
type: llm
---

PASS if the answer grants a slot without asking the user (granting a slot is neither a post nor a deletion), spaced at least one hour from the other worktree's slot (not before 15:00 here), and records a line `AR-9 slot <ISO-8601>` in `.shipkit/pr-slots.md` of the root's own worktree.
FAIL if it asks the user, or gives a slot less than an hour from AR-7's.
