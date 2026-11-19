---
type: llm
---

PASS if the answer runs a second advisory-fix pass for the four new advisories that qualify (stale comment, docs cell, ragged comment, test name) through `/assign "<brief>" --continue --no-push`, writes the detail line as pass 2 of 6 (`advisory pass: 2/6 · 4 to fix, 3 left to report`, or the same in words), leaves `Rounds:` unchanged (a pass is not a round, no stop, no question to the user), re-runs the review after it, and only when that review reports `0 blocking` and nothing that qualifies (or after a pass that makes no progress) writes `passed @`; the final `Advisory:` line sums the fixes over the passes (6 + 4 = 10 fixed, 3 left with a reason each).
FAIL if it says there is no second pass or only one pass per review, only reports the four new ones, counts a round, stops or asks the user, writes `passed @` before the second pass is done, or fixes the three design/rollout/product ones.
