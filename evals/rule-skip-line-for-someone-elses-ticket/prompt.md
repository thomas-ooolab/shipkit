---
description: "Observer: a QC post about a ticket that is certainly someone else's gets one short sentence."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/developer observer. A QC post in #qc says AR-9 failed. Jira: the assignee is Alice, the reporter is Bob; I am neither, and none of the commits or branches of AR-9 is mine (all read this turn). What does the skill print in the terminal?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
