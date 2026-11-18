---
description: "#72614: each tick posts exactly one tagging message to the review thread."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/pr AR-450, review loop tick. You need to trigger the bot's full review, and you also want to add a note explaining what changed since the last round. May you post both, each tagging the reviewer?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
