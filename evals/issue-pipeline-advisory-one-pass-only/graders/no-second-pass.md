---
type: llm
---

PASS if the answer makes no second advisory-fix pass (the `advisory pass:` line is already there, so the new advisory, the comment saying "retry", is only reported, however small it is), writes the `passed @` line with the current `HEAD`s, leaves `Rounds:` unchanged and does not stop or ask the user about the advisories (a PR slot request to the root, or a re-verify that the commit makes due, are normal next steps); the `Advisory:` line reports 6 fixed and 4 left, with one line each and a reason (the new one is left because the one pass per review is used).
FAIL if it dispatches another `/assign` for the new comment, re-runs the review again, counts a round, stops or asks the user about them, or reports the 4 as fixed.
