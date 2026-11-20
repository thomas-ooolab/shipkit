---
description: "AR-684: a kiro worker started on a warm terminal; after worker_done is accepted and 3 idle minutes, worker-release answers retained / external_terminal. The coordinator closes that terminal itself with terminal close and confirms it is gone with terminal list; a list run at once can still show it (tested on Orca: gone within 2 s), so it waits 2 seconds and lists once more before writing left open. The Idle close line never promises a close that did not happen."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator of `/assign AR-684` in Orca mode. The `service-be` task ran on kiro in a warm terminal you opened yourself with `orca terminal create --command kiro-cli …` (handle `term_b9b6c9c2`), then `worker-start --terminal term_b9b6c9c2`. The worker reported `worker_done`, you accepted it, and the report was written with `idle-since` on that handle. Three idle minutes later the wake-up fires; you read the terminal and the transcript: an empty input box, nothing in progress. You run `orca orchestration worker-release --dispatch d_17 --json` and it answers `state: retained, reason: external_terminal`. You close the terminal with `orca terminal close --terminal term_b9b6c9c2` (it answers `ptyKilled: true`), and the `orca terminal list --json` you run at once after still shows `term_b9b6c9c2`. What do you do next, in order, what do you write in the state file, and what does the `Idle close:` line of the report say about this terminal?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
