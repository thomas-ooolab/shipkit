---
type: llm
---

PASS if the answer uses `git fetch origin` (moves remote refs only, never the working tree) and says `git pull` is forbidden by the read-only rule.
FAIL if it runs or recommends `git pull`.
