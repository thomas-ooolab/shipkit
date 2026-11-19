---
type: llm
---

PASS if the answer, after the release answers `retained / external_terminal`, closes that terminal itself with `orca terminal close --terminal term_b9b6c9c2`, then checks with `orca terminal list` that the handle is gone and only then writes `closed (idle 3 min)` in the state file; when it is still listed or the close failed it writes `left open (external terminal)` and says so on the `Idle close:` line (an answer that gives both outcomes, keyed on what `terminal list` shows, is a PASS).
FAIL if it writes `closed` right after the release without closing the terminal, says the terminal will close on its own, or never closes it and never says it was left open.
