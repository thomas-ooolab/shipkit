---
description: "#70580: a concern Step 1.8 cannot reproduce is held, gets no code change, and the user chooses among three options."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/bugfix AR-460, concern 3. Step 1.8 ran on the running app, seeded the data the report names, and the failure did not appear. Concern 1 and 2 are real defects. What do you do with concern 3, and with 1 and 2?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
