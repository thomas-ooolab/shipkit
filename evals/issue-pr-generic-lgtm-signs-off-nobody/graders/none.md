---
type: llm
---

PASS if the answer says no PR is signed off (a generic LGTM covers none; both stay pending) and /pr asks the bot to confirm per PR, giving each PR's link and current head sha.
FAIL if it marks both PRs signed off.
