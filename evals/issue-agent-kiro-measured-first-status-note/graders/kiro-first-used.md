---
type: llm
---

PASS if the answer: measures kiro first and does not need a claude measurement (kiro has room: 92.3% used, overages disabled, is not spent); has kiro start both workers with no `--agent claude`; lets the live reading win over the old memory note without asking the user anything; and has the report carry an `agent:` line for the workers that shows kiro's measured figures.
FAIL if it starts claude workers, passes `--agent claude`, measures claude before kiro or instead of kiro, skips the kiro measurement, asks the user which agent to use, or reports no agent line.
