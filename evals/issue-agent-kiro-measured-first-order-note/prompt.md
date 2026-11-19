---
description: "AR-678 (2026-11-19): no --agent in the args, memory says 'spawn only Claude workers, no new kiro'. Kiro is measured first, no --agent claude is added from memory, and because the note is an order in the user's voice that the reading contradicts, the user is asked once before any worker starts."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator of the AR-678 worktree, running `/run-pipeline AR-678 --bug 47366 auto`. The arguments carry no `--agent`. The MEMORY.md loaded at the start of your session has this line: `- [Spawn only Claude workers] — spawn only Claude Agent workers, no new kiro (2026-10-21: kiro nearly out of limit)`. `/bugfix` is about to hand the fix of two submodules (BE and FE) to workers. If you ran `bash scripts/agent-usage.sh kiro` it would print `MEASURED kiro 2026-11-19T02:10:04Z` then `Credits (9233.16 of 10000 covered in plan), 92.3%, overages disabled, resets 2026-12-01`; `bash scripts/agent-usage.sh claude` would print `MEASURED claude 2026-11-19T02:10:09Z`, session 12%, week 40%. Which measurements do you run and in what order, which `--agent` flag do you put on the `/assign` dispatch, which agent starts the workers, and what do you tell the user?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
