---
description: "AR-676: /merge finds the prs stage by its name; in the bug flow that is stage 4, not 5."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/merge AR-460, a bug-flow ticket. Its .shipkit/pipeline-AR-460.md checklist reads:
- [x] 1 bugfix — fixed
- [x] 2 verify — PASS
- [x] 3 review — PASS
- [x] 4 prs — 1 PR, review loop clean, signed off
- [ ] 5 merged
and .shipkit/pr-AR-460.md does not exist (/pr deleted it). Can /merge confirm the reviewer's sign-off, or does it stop? Say which line it reads.

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
