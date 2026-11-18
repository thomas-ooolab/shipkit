---
type: llm
---

PASS if the answer says the failure signature differs (REQ-3 gone, REQ-5 new), so it counts as progress, the same-signature stop does not apply, and the loop goes on until the cap of 3 rounds per stage or 6 per ticket.
FAIL if it stops as no progress.
