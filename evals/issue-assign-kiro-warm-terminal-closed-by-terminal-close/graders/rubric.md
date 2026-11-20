---
type: llm
---

PASS if the answer, after the release answers `retained / external_terminal` and the `terminal close`, does not conclude from the first `terminal list` (run at once, still showing `term_b9b6c9c2`) that the terminal stayed open: it waits a couple of seconds and lists once more, and writes `closed (idle 3 min)` (or `closed (accepted)`) only when the handle is gone on that second list; when it is still listed then, or the close failed, it writes `left open (external terminal)` and says so on the `Idle close:` line (an answer that gives both outcomes, keyed on the second `terminal list`, is a PASS).
FAIL if it writes `left open` from the first list without listing again, writes `closed` while the handle is still listed, never closes the terminal itself, or says the terminal will close on its own.
