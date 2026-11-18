---
description: "Run-pipeline loop: only exit 5 of the push-window wait is a no-op; exit 2 is an error that is reported."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-478 auto, waiting for the push window with `notify-desktop.py --wait-only`. The command exits 2 and prints a usage message on stderr. What does the loop do?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
