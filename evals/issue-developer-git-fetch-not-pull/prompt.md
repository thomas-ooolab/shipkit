---
description: "#38990: the developer skill is read-only; git fetch is the one allowed git write and git pull is forbidden."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/developer, answering a Slack question about the digest. You need the latest code of the ticket's repo before you answer. Which git command do you run: git pull or git fetch?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
