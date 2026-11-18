---
description: "#70787: a waiting reason that changes only in digits keeps the original Waiting since clock."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-460, class B stop: `Status: waiting-user · 2 open questions`, `Waiting since: 09:00`. The PO answers one; the reason is now '1 open question'. What happens to the Waiting since line, and is the user notified again?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
