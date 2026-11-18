---
type: llm
---

PASS if the DM text names the QC engineer as the real Slack mention `<@U0510JSBPV5>` and the plain handle `chi.ttk` does not appear in it outside backticks (no `@chi.ttk`, no Jira accountId).
FAIL if the draft names her as plain text (`chi.ttk`, `@chi.ttk`, "Kim Chi", "chị Chi"), or uses the Jira accountId or `@[Name](accountId)`.
