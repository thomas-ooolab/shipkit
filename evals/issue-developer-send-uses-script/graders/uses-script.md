---
type: llm
---

PASS if the answer uses the plugin script `scripts/send-when-ready.sh <handle> "<message>"` (as a background task, not the foreground) for the wait and the send, writes no wait loop or send script of its own (no scratch file, no `head -1 | grep` over `wait-for-agent.sh`, no hand-written `terminal wait` + `terminal send`), and for the non-zero exit says the message was NOT sent (names RESULT=not-ready / the login screen) and never reports it as sent or running.
FAIL if it hand-writes the Ready or send loop, runs the wait in the foreground, or reports a non-zero exit as sent, pinged or running.
