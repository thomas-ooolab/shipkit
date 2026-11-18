---
description: "AR-678: an auto run does not stop because both sides touched a file when git merge-tree is clean."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/run-pipeline AR-478 auto, at the point of dispatching /merge. The PR changed api/openapi-extras.md and the destination branch changed the same file since. `git merge-tree --write-tree --name-only origin/<destination> <PR head>` exits 0, no conflict. The file is not an input of the code generator. Does the auto run stop, or does it dispatch /merge?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
