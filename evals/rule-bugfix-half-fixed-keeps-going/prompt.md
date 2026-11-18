---
description: "v0.36.111: when the latest code fixes only half, the evidence is posted, the ticket is not handed back, and the rest is fixed right away."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/bugfix AR-460. QA's comment reports two concerns. On the latest code concern 1 is fixed (/verify PASS, fixing commit named) and concern 2 is still broken. bugfix-coverage.py printed partial. What does /bugfix do now?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
