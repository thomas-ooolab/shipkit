---
description: "#70649: a signature that differs in any way counts as progress; only the round caps end the loop."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-460 auto, verify stage. Before the fix round /verify failed REQ-2 and REQ-3. After one fix round the re-run fails REQ-2 and REQ-5. Is that 'no progress'? Does the loop go on?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
