---
type: llm
---

PASS if the answer keeps `Waiting since: 09:00` (the wording differs only in digits, so it is the same waiting cause) and sends no new notification for the count change.
FAIL if the clock restarts or the user is notified again.
