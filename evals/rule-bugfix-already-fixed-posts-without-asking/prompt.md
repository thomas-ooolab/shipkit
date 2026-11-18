---
description: "v0.36.111: a bug already fixed on the latest code gets its evidence posted to the source without asking, tagging the reporter; the ticket goes back to them."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/bugfix AR-460. QA's comment on the Jira ticket reports two concerns. /verify --concern passed for both on the latest code, and the fixing commit is named for each; bugfix-coverage.py printed all-fixed-on-latest. What does /bugfix do now? Does it ask me first?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
