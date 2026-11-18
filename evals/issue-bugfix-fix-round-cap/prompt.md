---
description: "#70620: at most 3 fix rounds per concern, and a round that fails at the same step as the last ends the loop."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/bugfix AR-460, concern 2. Round 1: /verify FAILED at step 'click Export, expect 3 rows'. You fixed again; round 2: /verify FAILED at the same step 'click Export, expect 3 rows'. Do you start round 3?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
