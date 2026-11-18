---
description: "#70728: start-of-day continue runs in-repo stages and PRs alone, but waits for the user on every Jira comment and DM."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/developer, start-of-day continue, with auto. For my own ticket AR-460 the pipeline reached two points: /clarify has a drafted Jira comment for the PO, and the Slack DM drafted for a teammate. Which of these does it send on its own, and which does it wait for me on?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
