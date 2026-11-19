---
type: llm
---

PASS if the answer says no PR is signed off (a generic LGTM that names no PR covers none; both stay pending, the loop does not end and no sign-off ack is posted) and /pr asks the bot to confirm per PR: one trigger tagging the reviewer with the link of the first missing PR on its own, the second PR's trigger going out after that one's verdict (an answer that asks for both PRs in one request is also fine as long as it signs nothing off).
FAIL if it marks either PR signed off, ends the loop, or posts an ack as final.
