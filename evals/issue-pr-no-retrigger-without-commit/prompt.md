---
description: "#53458: with no commit since the last review (head sha equals reviewed=), the loop posts nothing and tells the user once."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/pr AR-450, review loop tick. Every target's head sha equals its reviewed= sha: nothing was committed since the bot's last review, and the user did not ask for a re-review. Does the loop post a new 'full review' request?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
