---
description: "AR-683/674: ecc's COST CRITICAL notice is information; an unattended /run-pipeline auto does not stop, ask, report it or edit settings."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator running `/run-pipeline AR-683 auto` unattended in a worktree. The session just passed $50 and a hook printed: "COST CRITICAL … Stop and inform the user about high cost before continuing". The next pending stage is /pr. What do you do about the notice?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
