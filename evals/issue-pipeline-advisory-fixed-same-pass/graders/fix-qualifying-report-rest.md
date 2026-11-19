---
type: llm
---

PASS if the answer, without asking the user and although `auto` is not set, judges the advisories itself and has them fixed in one pass through `/assign "<brief>" --continue --no-push` whose brief quotes exactly the qualifying ones: (1)-(5) stale comment/spec/assertion text, (6)-(7) the wrong REQ-ID, (8) the duplicated check, (9) the copied fake (the exact numbers need not match; (8) and (9) may be listed as simplifications). It leaves (10) design opinion, (11) rollout note, (12) product decision and (13) API-contract change unfixed and names them in the final report with a reason (an `Advisory:` line such as `<n> fixed, 4 left`). After the fix it runs `/review-changes` again because the commit made the PASS stale, says that this dispatch and re-run are not a round (`Rounds:` stays 1/6), and writes the `passed @` line only after that.
FAIL if it leaves all 13 advisories (or files them as follow-ups), asks the user whether to fix them, stops, fixes (10)-(13) or says to fix them, counts the pass as a round, or skips the re-review.
