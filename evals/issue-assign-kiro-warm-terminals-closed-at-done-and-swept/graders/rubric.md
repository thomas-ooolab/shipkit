---
type: llm
---

PASS if the answer does all of these:
(a) closes `term_b1` now, when its `worker_done` is accepted and the screen reads idle (an input box, nothing in progress), without waiting for a 3-minute timer: `worker-release` (it answers `external_terminal`), then `orca terminal close --terminal term_b1`, then `orca terminal list` must no longer show it, and only then does it write `closed` beside it;
(b) before writing `Status: done` it runs an end-of-run sweep (`orca terminal list --worktree current`) and closes `term_a1` and `term_a2` the same way (they are recorded in the state file as kiro warm terminals and have no running worker), confirming with `terminal list`;
(c) leaves `term_notes` open (it is the user's own, not one the run opened);
(d) the report carries one `Idle close:` line per handle (`closed`, or `left open: <why>` for one that could not be closed).

FAIL if it waits for a timer to close `term_b1`, says `worker-release` closes these terminals, leaves `term_a1` / `term_a2` open without saying so, closes `term_notes`, or writes `Status: done` with no sweep.
