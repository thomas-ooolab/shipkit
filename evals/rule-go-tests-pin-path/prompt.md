---
description: "AR-676: a Go test that names a changed file by path is run even without importing the package."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/pr AR-476, Go submodule. The diff changes only handlers/studycourse/service.go. The import graph gives one direct dependent, handlers/report. internal/pkg/routeauthz/parity_test.go imports neither package but contains the text 'handlers/studycourse/service.go:452'. Which packages does /pr run, and how does the report list each?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
