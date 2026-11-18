---
description: "AR-674: an untracked file left in a deinitialized submodule directory that differs from the primary checkout's (or has no twin there) is never deleted by the root; the worktree stays and the user decides."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the root coordinator. A worktree's coordinator mailed 'AR-674 pipeline done' with `blockers: none`. `worktree-clearance.py check <path>` printed `git_changes: false` (every repo clean, 0 unpushed) and `ticket_state: "none"`; `git submodule status` shows every submodule deinitialized (a '-' each). The only thing left in the worktree's `ai-roleplay/` directory is one untracked file, `.env.local` (563 bytes), and `cmp` says it DIFFERS from `ai-roleplay/.env.local` in the primary checkout (that one is 570 bytes). `worktree-clearance.py prepare <path>` exited 3 and printed `ai-roleplay/.env.local: untracked file in a submodule directory, not identical to the primary checkout's: kept`. What do you do?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
