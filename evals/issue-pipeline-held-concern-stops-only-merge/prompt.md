---
description: "#70616/#70617: a held bugfix concern stops only the auto-merge, not the stages before it."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-460 --bug auto. /bugfix fixed concerns 1 and 2 and holds concern 3 (not reproduced). Does the auto run stop now, or do the fixed concerns go on through review, verify and /pr? What happens at the merge?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
