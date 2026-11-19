---
description: "AR-678 (2026-11-19): mail to the root arrived 9 minutes late while the root sat idle. The worktree checks delivered_at about 150 s after a send, wakes the root only from an idle empty input box, once per message, and records it on the detail line."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator of the AR-678 worktree, running `/run-pipeline AR-678 --bug auto`. At 08:42:31 you sent the PR slot question to the root (`orchestration send --to run:run_11d0f461afbc`, subject `AR-678 question: pr slot`); the `send` printed message id `msg_19f3d6d966ba`. It is now about 08:45. Your state file has `Status: waiting-user · asked the root: pr slot`. You have not checked anything since the send. What do you do now, in order, and what does the state file's detail line say before and after? Then suppose the check shows `delivered_at` is empty, the root's terminal is idle and its input box is empty: what exactly is done? And what if the box holds a half-typed `/merge AR-6`, or the root is in the middle of a turn? And what if the box shows only a dim suggestion, `run the tests again`, that reads the same in two reads 15 seconds apart?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
