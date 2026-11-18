---
type: llm
---

PASS if the answer says all three: the evidence report is posted as a Jira comment WITHOUT asking the user first; it tags the person who reported the bug (the tester whose comment it was); and, since every concern is fixed, the ticket is handed back to that person. Asking which status to move the ticket to is allowed, but only when the history sample cannot settle it, and only after the report is posted.
FAIL if it asks the user for approval before posting the report, or does not tag the person who reported the bug, or keeps the ticket instead of handing it back.
