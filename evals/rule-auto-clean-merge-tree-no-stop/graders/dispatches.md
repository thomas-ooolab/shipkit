---
type: llm
focus: last_message
---

PASS if the answer says the auto run does NOT stop on the shared file (the merge-tree test is clean) and dispatches /merge.
FAIL if it stops, calls it a class C conflict, or says overlapping files always stop.
