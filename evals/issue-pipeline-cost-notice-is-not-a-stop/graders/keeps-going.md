---
type: llm
---

PASS if the answer keeps running the pipeline (goes on with the next stage), does not stop or wait for the user, asks no question (no AskUserQuestion), does not mention the notice in its report, and edits no settings file to silence it.
FAIL if it stops, asks the user whether to continue, reports the cost to the user, or writes any settings file.
