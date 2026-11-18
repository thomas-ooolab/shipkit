---
description: "#70526: the bot reads only links from Slack, so already-answered points go in the PR description's Decisions block."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/pr AR-450. The PO already settled OQ-2 on Jira. How does the review bot get to know it, so it does not ask again? The trigger message in Slack carries only the PR links.

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
