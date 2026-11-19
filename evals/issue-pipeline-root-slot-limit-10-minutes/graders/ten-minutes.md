---
type: llm
---

PASS if the answer says the PR slot question's limit is 10 minutes, which has run out (08:52:31), so it asks the user in this terminal "start /pr now?" (their yes is the slot), rewrites the detail line to `asked the user, root silent @ <time>: pr slot` and `Status: waiting-user · asked the user, root silent: pr slot`, stops re-arming the delivery check, and types nothing into the root's terminal; and it says every other question to the root keeps the 2-hour limit.
FAIL if it keeps waiting for the slot question until 2 hours have passed, types into the root's input box, or says the 10-minute limit applies to every root question.
