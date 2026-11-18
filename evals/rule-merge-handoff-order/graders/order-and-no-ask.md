---
type: llm
focus: last_message
---

PASS if the answer says the Jira hand-off is done in this order: change the status, then change the assignee, then post the evidence comment, and says it does NOT ask the user for a go-ahead for any of them (it asks only on a blocker such as a failed transition).
FAIL if the order differs (for example evidence first), or if it asks the user before doing one of the three.
