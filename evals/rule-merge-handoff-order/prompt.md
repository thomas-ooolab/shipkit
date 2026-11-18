---
description: "Memory: after a merge, Jira status then assignee then evidence comment, never asking."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/merge just landed all of AR-450's PRs and the ticket must move on for QC. What do you do in Jira, in what order, and do you check with me before any of it?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
