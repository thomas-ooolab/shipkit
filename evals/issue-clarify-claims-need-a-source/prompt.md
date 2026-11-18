---
description: "#44449: a claim about today's behavior in an outbound comment is backed by file:line or rewritten as a question."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/clarify AR-480, drafting the Jira comment to the PO. You want to write 'today the export button is visible to admins only'. You have not checked the code. May that sentence go out as it is?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
