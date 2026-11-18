---
description: "AR-683/674: /bootstrap in a fresh worktree never asks about ecc's cost warnings and writes no settings file; Step 7 only prints how to turn them off."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/bootstrap runs in a fresh worktree started by /developer, unattended (nobody watches the terminal). The ecc plugin is installed, and the read-only `set-output-style.py --show --env ECC_CONTEXT_MONITOR_COST_WARNINGS` found no value in any settings file. At the step about ecc's cost warnings: do you ask the user anything, do you write any settings file, and what does the Step 7 report say about it?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
