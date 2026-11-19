---
description: "AR-672: the review re-run after an advisory-fix pass reports 0 blocking and new advisories that qualify; the coordinator runs the next pass (2/6), not a round, then re-runs the review."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/run-pipeline AR-672 --bug auto`. Stage 3 review reported `0 blocking, 9 advisory`; you fixed the qualifying ones in one `/assign "<brief>" --continue --no-push` pass (the state file has `- detail: advisory pass: 1/6 · 6 to fix, 3 left to report`), which committed, and the review was run again. This second run reports `0 blocking, 7 advisory`: three are the ones you left (design opinion, rollout note, product decision) and four are new: a stale "per-IP" comment, a docs table cell that still says "per IP", a ragged comment, and a test name that says "retry" where the code says "reserve". What do you do next, what does the state file get, and what does the final report's `Advisory:` line say?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
