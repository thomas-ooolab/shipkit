---
description: "AR-672: ten kiro warm terminals stayed open over a run of two waves and four advisory passes, because the only close was Step 6's 3-minute timer and worker-release answers external_terminal. A kiro warm terminal is closed when its worker_done is accepted and the screen reads idle; before Status: done the end-of-run sweep closes any the run left open and prints one Idle close line per handle."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator of `/run-pipeline AR-672 auto` in Orca mode. The review's advisory passes called `/assign "<brief>" --continue --no-push` twice. Pass 1 started two kiro workers, each in a warm terminal you opened yourself with `orca terminal create --command kiro-cli …`: `service-be` in `term_a1` (dispatch `d_1`) and `service-fe` in `term_a2` (`d_2`). Pass 2 started one: `service-be` in `term_b1` (`d_3`). Each sent `worker_done` with `outcome=succeeded` and you accepted it (the commits are local, `--no-push`). `orca orchestration worker-release` answers `state: retained, reason: external_terminal` for each one. The state file records all three as `terminal=<handle> (kiro, warm terminal)`. The `/assign` of pass 1 ended without ever starting the 3-minute idle timer. `term_a1` and `term_a2` are still open; you have just accepted `d_3`'s `worker_done`, and the review passes, so the pipeline is about to write `Status: done`. `orca terminal list --worktree current` also shows `term_notes`, a terminal the user opened by hand. What do you do now, in order, for `term_b1`, for `term_a1` and `term_a2`, and for `term_notes`; what do you write in the state file; and what lines does the run's report carry about the terminals?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
