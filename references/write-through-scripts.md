# Writing to Slack or Jira — always through the plugin's scripts

Every write to Slack or Jira from the user's session goes through this plugin's scripts: `scripts/post-slack.js` (post, edit, delete) and
`scripts/jira-comment.py` (post, edit, delete). Never an MCP write tool: not `mcp__claude_ai_Slack__slack_send_message`,
`slack_send_message_draft`, `slack_schedule_message` or `slack_create_canvas`; not the Atlassian `addCommentToJiraIssue`, `editJiraIssue`,
`createJiraIssue` or `transitionJiraIssue`. The MCP connectors stay for **reading**.

Why: the script posts with the user's own token, sends a real @mention (Jira stores an MCP mention as plain text, so nobody is
notified), and sits behind the draft, humanize and approval steps of the skill that calls it.

One exception, Jira only: `jira-comment.py` exits 3 (`JIRA_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` unset) → `addCommentToJiraIssue` is the
fallback, and the user is told the mentions will not notify anyone. Slack has no fallback.

Taking a message back: `node scripts/post-slack.js delete <channel_id> <ts>` (Slack), `jira-comment.py delete <TICKET> <comment-id>`
(Jira). Never a hand-made `chat.delete` or REST call with the token.

| Excuse | Reality |
|---|---|
| "The MCP send tool is already in the session, it's handier" | It posts as the wrong identity, tags no real mention and skips the humanize and approval steps. The script does all three. |
| "It's only a quick DM or a ping" | A DM is a message in the user's name: same script, same approval. |
| "The script has no delete, so I'll call the API by hand" | It has: `post-slack.js delete`. A hand-made call with the token is never the answer. |
