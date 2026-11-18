---
description: "#70806: a PASS is current only while the recorded shas equal HEAD; /pr's own commits make only verify stale."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-460 auto. review PASS and verify PASS were both recorded at parent HEAD abc1234. /pr's own review loop then committed a fix on the branch (HEAD def5678). Which of the two PASS lines is stale now?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
