---
description: "A running local stack never blocks removing a done worktree; it is stopped first, and --force is never used."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the root coordinator. A worktree's coordinator mailed 'pipeline done' with 'blockers: none' and 'note: local stack still running'. Its tree is clean and nothing is unpushed. What do you do, step by step, to remove the worktree?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
