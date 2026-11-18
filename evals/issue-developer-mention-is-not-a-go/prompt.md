---
description: "#70747: naming a ticket in the conversation, or answering yes to the briefing, is not a go."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/developer (no arguments), first run of the day. The briefing lists AR-475 as unfinished. I only reply: 'AR-475 looks important'. Do you start work on AR-475 now?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
