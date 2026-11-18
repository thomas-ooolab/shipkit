---
type: llm
focus: last_message
---

PASS if the answer says: fix only the correctness item through /assign, put the three nits in the follow-ups (.shipkit/pr-<ticket>.md under ## Follow-ups and the pipeline file's detail line), mark the PRs signed off, and hand control back to the caller (/run-pipeline) without stopping for the user.
FAIL if it stops and asks the user to decide /merge, or fixes the nits too.
