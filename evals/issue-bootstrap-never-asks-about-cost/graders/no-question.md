---
type: llm
---

PASS if the answer asks the user nothing about ecc's cost warnings (no AskUserQuestion, no blocking prompt), writes no settings file (no settings.local.json, no `--env ... =off`), and says the Step 7 report prints a one-time tip with the command to turn the warnings off (and undo it).
FAIL if it asks "Turn off ecc's cost warnings?" or any question about it, or writes `ECC_CONTEXT_MONITOR_COST_WARNINGS=off` or any settings file, or omits the tip entirely.
