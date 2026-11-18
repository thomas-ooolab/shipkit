---
description: "A user's plain request that /run-pipeline is for; the skill must be the one Claude picks."
tags: [routing]
max_turns: 8
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
---

Take AR-461 through the whole pipeline with one command, in auto mode, and resume where it stopped.
