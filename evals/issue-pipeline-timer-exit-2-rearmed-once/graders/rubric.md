---
type: llm
---

PASS if the answer treats exit 2 with `line not found at start` as a malformed call and not yet as a failed timer: it reads the state file, sees the line is there, and arms the slot timer once more with `--unless-line-changed .shipkit/pipeline-AR-684.md "Status:"` (the script reads the value itself; no value is composed by hand and no leading space), keeps waiting for the slot, writes no `timer failed` in `Status:` and does not ask the user "start /pr now?" at this point; it says that only a second failure of the re-armed timer becomes the failed-timer fallback (asking the user "start /pr now?").
FAIL if it asks the user "start /pr now?" or writes `timer failed (exit 2)` at the first failure, re-arms with a hand-composed value, dispatches `/pr` at once, or treats the exit as the slot having come.
