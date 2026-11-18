---
description: "A user's plain request that /review-changes is for; the skill must be the one Claude picks."
tags: [routing]
max_turns: 8
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
---

Review the changes on my feature branch before I open a PR. Report findings only, do not fix anything.
