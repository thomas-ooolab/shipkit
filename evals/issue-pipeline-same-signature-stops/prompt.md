---
description: "#70806: a fix loop stops at once when a round's re-run has an identical failure signature."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-460 auto, verify stage, round 1 of the fix loop. Before the round /verify failed REQ-2 and REQ-3. After one fix round the re-run fails exactly REQ-2 and REQ-3 again. Does the loop run a second round?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
