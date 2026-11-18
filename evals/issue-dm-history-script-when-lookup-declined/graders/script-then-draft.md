---
type: llm
---

PASS if the answer reads the DM history with Thang before any draft exists, using the plugin's `slack-dm-history.js` (or an equivalent read of that DM), and says the declined `slack_search_users` call does not release the step; the draft it later shows takes its language and form of address from what the user wrote in that DM.
FAIL if it drafts or shows a DM without reading the history first, treats the declined lookup as a reason to skip the history, or plans a draft with the pronouns left out instead of reading the history or asking.
