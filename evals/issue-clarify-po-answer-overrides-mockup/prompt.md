---
description: "#71102: a PO answer that contradicts a mockup-derived tick reopens it, keeping the old text after 'previously:'."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/clarify AR-480. In open-question.md the item `- [x] OQ-4 — ... decided (design-recon: the mockup shows a Delete button)` was ticked from the mockup. The PO now answers on Jira that nobody may delete. What happens to OQ-4?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
