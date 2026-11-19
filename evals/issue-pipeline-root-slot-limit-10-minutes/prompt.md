---
description: "The PR slot question waits 10 minutes for the root, not 2 hours, before asking the user 'start /pr now?'; any other question to the root keeps the 2-hour limit."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator of the AR-678 worktree, running `/run-pipeline AR-678 --bug auto`, stage `prs`, no PR exists yet. You sent the root the PR slot question at 08:42:31 (message `msg_19f3d6d966ba`). At 08:45 and again at 08:48 the delivery check printed `RETRY input box is not empty or not found, nothing typed` (the root's input box held half-typed text). It is now 08:52:40, the message still has no answer and `delivered_at` is still empty. What do you do now, and what is the exact limit you apply? Which limit applies to any other question a worktree sends to the root?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
