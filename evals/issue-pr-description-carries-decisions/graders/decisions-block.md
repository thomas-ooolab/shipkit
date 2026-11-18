---
type: llm
---

PASS if the answer says the review bot reads only the PR links from Slack but also reads the PR description, so the resolved item goes in the PR description's 'Decisions made' block (between the shipkit:decisions markers, as an OQ-n line with a reason and a proof reference).
FAIL if it says to explain it in the Slack message.
