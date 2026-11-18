---
type: llm
---

PASS if the answer says both the Jira comment draft and the DM draft wait for the user's approval (every Jira comment and every DM the skill drafts), while in-repo stages, /pr and the review Slack thread, and /merge when its preconditions hold run alone.
FAIL if it sends either the Jira comment or the DM without approval.
