---
description: "#72614: a Jira comment from the PR loop waits for explicit approval, while a Slack post does not."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/pr AR-450, review loop. The reviewer bot raised a product question that must go to the PO on Jira. You also have a Slack confirmation reply for the bot. Which of the two do you post on your own, and which waits for me?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
