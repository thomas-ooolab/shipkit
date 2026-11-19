---
description: "AR-672: the advisory passes stop at six, or earlier when a pass makes no progress (the fixer committed nothing, or the same qualifying advisories come back); passes are not rounds."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/run-pipeline AR-672 --bug auto`. The state file has `Rounds: 1/6` and `- detail: advisory pass: 3/6 · 2 to fix, 1 left to report`. Pass 3 was dispatched through `/assign "<brief>" --continue --no-push`; its report says it committed nothing: it could not do either advisory (a stale "per-IP" comment in a file it could not edit and a docs cell). `HEAD` did not move. Separately, picture the same run one step later in another case: the state is `advisory pass: 6/6`, pass 6 committed, the review re-ran and reports `0 blocking, 2 advisory` that both qualify (a stale comment, a wrong label). What do you do in each of the two cases, what do you write, and what does the report say about the advisories left?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
