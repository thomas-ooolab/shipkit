---
description: "AR-683/680/674: a .shipkit holding only root-coordinator.md (a pointer) with a clean git is not in progress; the script decides, no worktree-checker, no question."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the root coordinator. A worktree's coordinator mailed 'AR-683 pipeline done' with `blockers: none`, and every PR of the ticket is merged. You ran `worktree-clearance.py check <path>` and it printed: `git_changes: false` (every repo clean, 0 unpushed), `ticket_state: "none"`, `shipkit: {exists: true, pipelines: [], other_state_files: []}`. The only file in the worktree's `.shipkit/` is `root-coordinator.md` (run, root_terminal, root_worktree, written: the root pointer /developer's run wrote). Which agents or checks do you use next, do you ask the user anything, and what do you do with the worktree?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
