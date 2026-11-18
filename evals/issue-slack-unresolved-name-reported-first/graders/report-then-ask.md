---
type: llm
---

PASS if the answer tells the user in one line, before any draft is shown, that hoa.ntp has no Slack user (not found), asks who that is, and does not leave "hoa.ntp" in a draft as plain text (no draft with the handle, no `@hoa.ntp`).
FAIL if it shows a draft that names hoa.ntp as plain text, drops the person silently, guesses an id, or posts.
