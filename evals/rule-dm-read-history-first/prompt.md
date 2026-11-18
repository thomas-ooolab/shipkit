---
description: "Memory: before a Slack DM, read the DM's history to match tone, register and pronouns."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

As the developer, send a Slack DM to Linh in my name saying the digest fix is live. What do you do before you write it?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
