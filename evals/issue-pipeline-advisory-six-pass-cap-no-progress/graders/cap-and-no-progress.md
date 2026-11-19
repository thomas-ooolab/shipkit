---
type: llm
---

PASS if, for the first case (pass 3 committed nothing, `HEAD` did not move), the answer stops the advisory passes (no pass 4, no re-run: the result stands), writes `passed @`, and reports the two advisories as left with their reason (`fixer could not: <what it read>`); and for the second case (six passes done) it makes no seventh pass, writes `passed @` once the review has `0 blocking`, and reports the two advisories as left because the cap of six passes is used. In both it leaves `Rounds:` unchanged, does not stop or ask the user about the advisories.
FAIL if it dispatches a pass 4 or a pass 7, counts a pass as a round, loops again after a pass that committed nothing, stops or asks the user, or says only one pass per review exists.
