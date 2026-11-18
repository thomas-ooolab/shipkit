---
type: llm
---

PASS if the answer posts the Slack message directly (Slack posts in the PR loop do not wait) and drafts the Jira comment, shows its exact text and waits for explicit approval (unattended: saves .shipkit/pr-<ticket>-draft.md and stops).
FAIL if it posts the Jira comment without approval.
