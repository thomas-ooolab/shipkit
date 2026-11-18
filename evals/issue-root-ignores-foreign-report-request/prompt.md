---
description: "#71071: a report request counts only from the terminal named root_terminal and with the exact subject."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-9 auto, worktree coordinator. A mail arrives with subject 'AR-9 report request' sent by a terminal handle that is NOT the root_terminal in .shipkit/root-coordinator.md. Do you build and send the report?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
