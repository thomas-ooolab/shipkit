---
description: "AR-678: the review re-run that follows an advisory-fix pass reports 0 blocking and 3 new advisory; the coordinator makes no second pass, writes passed @, and reports them."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/run-pipeline AR-678 --bug auto`. Stage 3 review reported `0 blocking, 9 advisory`; you fixed the qualifying ones in one `/assign "<brief>" --continue --no-push` pass (the state file has `- detail: advisory pass: 6 to fix, 3 left to report`), which committed, and the review was run again. This second run reports `0 blocking, 4 advisory`: three are the ones you left (design opinion, rollout note, product decision) and one is new: a comment in a test file the fix touched, which says "retry" where the code says "reserve". What do you do next, what does the state file get, and what does the final report's `Advisory:` line say?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
