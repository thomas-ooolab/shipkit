---
type: llm
---

PASS if the answer says the comment is posted with shipkit's own script (`jira-comment.py`) and does not plan to write with the Atlassian connector or MCP tool. Naming the connector only as the thing not to use is fine.
FAIL if the write itself is planned through the Atlassian connector or MCP tool, or no posting command is named.
