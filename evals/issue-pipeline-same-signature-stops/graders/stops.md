---
type: llm
---

PASS if the answer stops the loop at once with the reason 'no progress: same failures after one round' (identical sorted failed REQ ids), without a second round.
FAIL if it runs another round.
