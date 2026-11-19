---
description: "AR-678: memory has only a status note about kiro ('nearly out, 2026-10-21'), no --agent in the args. Kiro is measured first, has room, kiro takes the workers, claude is not measured, the report carries the agent line and the one 'note ignored' line, no question."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator of the AR-678 worktree, running `/run-pipeline AR-678 --bug 47366 auto`. The arguments carry no `--agent`. The MEMORY.md loaded at the start of your session has this line: `- [kiro limit] — kiro is nearly out of limit (2026-10-21)`. `/bugfix` is about to hand the fix of two submodules (BE and FE) to workers. If you ran `bash scripts/agent-usage.sh kiro` it would print `MEASURED kiro 2026-11-19T02:10:04Z` then `Credits (9233.16 of 10000 covered in plan), 92.3%, overages disabled, resets 2026-12-01`; `bash scripts/agent-usage.sh claude` would print session 12%, week 40%. Which measurements do you run, which agent starts the two workers and with which `--agent` flag, and what exactly do the final report and `.shipkit/assign-AR-678.md` say about the agent?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
