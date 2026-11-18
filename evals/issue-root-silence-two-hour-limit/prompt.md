---
description: "#71010: the worktree's 2-hour limit for the root applies even when the root is relaying to a user who has not answered."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-9 auto. The worktree asked the root a question 2 hours ago. The root answered once: 'asking the user'. The user has not answered. Does the worktree keep waiting for the root, or fall back?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
