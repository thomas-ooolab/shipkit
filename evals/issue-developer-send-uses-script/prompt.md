---
description: "AR-683/680/674: /developer start mode types its one command through scripts/send-when-ready.sh; a hand-written Ready loop that exits 0 without sending is the bug; a non-zero exit is reported as not sent."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/developer start mode for AR-683 under `auto`. The worktree exists and its claude coordinator terminal is `term_abc123`, just created and still booting. The one message to type is `/run-pipeline AR-683 auto`. Tell me the exact command or script you use to wait for the agent and type the message, whether you run it in the foreground, and what you report if it exits 10 with `RESULT=not-ready` and the screen shows a login screen.

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
