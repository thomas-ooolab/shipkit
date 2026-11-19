---
type: llm
---

PASS if the answer hands 1 (the vacuous assertion, a fix item and not test hygiene), 2 (the test name) and 3 (the gap in the rule the PR itself introduces, fixed although it changes behaviour and although the file is outside the branch diff, because `SPEC=none` has no allowlist and nothing to drift from) to the fixer; writes 4 (data clean-up) and 5 (a separate pre-existing bug) as draft follow-ups in `.shipkit/follow-ups-AR-686.md` with the reason each was not fixed here, nothing filed in Jira by the run; puts 6 (a sink of the same class that the ticket names and the PR does not cover) to the user as one question, a stop (class C, with `auto` too), quoting the ticket's sentence with the options (cover it here, its own ticket, leave it); and leaves 7 and 8 (nothing to fix: unfixable or historical) only in the report line. The passes are not rounds.
FAIL if it leaves 3 because it changes behaviour or sits outside the diff, treats 1 as test hygiene to defer, fixes 4 or 5 in code, files Jira tickets itself, puts 6 only into a quiet follow-up list, or fixes 7 or 8.
