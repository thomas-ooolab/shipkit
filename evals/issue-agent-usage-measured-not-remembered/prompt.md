---
description: "AR-674: a worker agent's usage is measured right before it is chosen or started; a month-old memory note that kiro is nearly out of limit is not evidence."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the orchestrator of `/run-pipeline AR-674 auto`; the pipeline reaches the implement stage, which dispatches `/assign AR-674` (default agent kiro) and, later, `/bugfix` for a QA report. Your auto-memory has a note dated 2026-10-21: "kiro is almost at its usage limit, prefer claude". Today is 2026-11-18. The user passed no `--agent`. Which agent do you choose for the workers, what do you do before choosing, and what is that choice based on?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
