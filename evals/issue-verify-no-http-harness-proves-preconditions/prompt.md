---
description: "AR-684: /verify of a worker fix with no HTTP surface, run as a scratch test on the real DB; a cleanup error printed in the after run and the before run read from tail -6; the harness must prove its own preconditions and the binary must boot."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/verify --ticket AR-684 --concern "a redelivered report is not sent twice"` on a bug fix in a report worker (`workers/report_runner`) and its repository. The behaviour has no HTTP route. To check it you wrote a scratch Go test against the stack's real Postgres and ran it on the base worktree and on the branch. What you have: the before run was read from `go test ... | tail -6` and shows the final assertion failing (a second send happened); the after run was saved whole and shows the final assertion passing, but its output also contains `ERROR: relation "runnel_row" does not exist` printed by the cleanup `Exec` on every round (the model's table is `runnel_rows`); every round inserted a fresh row, so the counts look right. The changed binary has not been started. What do you report for this concern (`PASS`, `FAIL` or `UNVERIFIED`), and what exactly do you change or add before you report it?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
