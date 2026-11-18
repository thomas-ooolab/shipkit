---
description: "#70581: fixed means PASS plus a before-fix reproduction file; otherwise 'changed, not reproduced'."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/bugfix AR-460, concern 1. You shipped a change and /verify --concern returned PASS with its evidence file. Step 1.8 never reproduced the failure, so no '-before' file exists. What verdict word does the state file get for concern 1?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
