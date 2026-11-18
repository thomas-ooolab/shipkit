---
description: "#70582: a spec edit during a bugfix must cite a recorded decision; without one it is a product-decision concern."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/bugfix AR-460. After your fix you find that spec.md REQ-004 says the export is capped at 100 rows while the code (and the tester) expect 500. No Jira comment or PO answer records a decision about the cap. May you edit REQ-004 to say 500?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
