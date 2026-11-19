---
type: llm
---

PASS if the answer: measures kiro first (`agent-usage.sh kiro`), before any claude choice; does not put `--agent claude` on the dispatch (a flag taken from memory is not explicit, and the measured kiro has room: 92.3% used, overages off, is not spent); treats the memory line as an old note that does not replace the reading; and because the note is worded as the user's own order and the reading contradicts its reason (kiro has room), asks the user once, before any worker starts, quoting the note and the figures and offering kiro and claude (in a pipeline run a stop such as `Status: waiting-user`), instead of choosing silently. No worker starts before that answer. Saying that a claude measurement would follow only if the user then picks claude is fine.
FAIL if it passes `--agent claude` or starts claude workers because of the memory line, never measures kiro (or measures only claude, or claude first), silently uses claude, or silently ignores the note without asking.
