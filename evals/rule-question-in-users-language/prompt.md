---
description: "The language line the SessionStart hook gives is obeyed: a question to the user is in that language."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
append_system_prompt: "Language for everything you say to this user (questions, reports, summaries, drafts for them): Vietnamese (vi), from memory: \"ask in Vietnamese\". Pass `language: vi` to every agent or worker you start."
---

I want to run /clarify on AR-450 but the PO's two answers contradict each other. Ask me which one to keep, with two options.

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
