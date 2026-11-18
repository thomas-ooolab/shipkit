---
description: "#71900: a question ends the PR-slot timer; after the answer the worktree asks the root for the slot again."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-460 auto. The worktree is waiting for its PR slot (granted for 14:00). At 13:10 a real question for the user comes up, and the user answers at 13:30. The stage is still `prs` with no PR open. What does the worktree do after the answer?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
