---
type: llm
focus: last_message
---

PASS if the answer says sign-off IS confirmed, reading the line named `prs` (stage 4 here) of the pipeline file, and /merge goes on.
FAIL if it stops or refuses because stage 5 is unchecked, or because pr-AR-460.md is missing.
