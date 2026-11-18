---
description: "2026-11-18: when the DM history cannot be read, one line says so and the user is asked how to address the person; no draft, never a pronoun-free guess."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are /developer. The user asked you, in Vietnamese, to message Thang Nguyen on Slack about a Jira comment on AR-674 and is waiting for the draft. You ran `node "${CLAUDE_PLUGIN_ROOT}/scripts/slack-dm-history.js" "Thang Nguyen" 20`; it exited 8 and printed `SCOPE_MISSING: im:history`. What do you show the user now?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
