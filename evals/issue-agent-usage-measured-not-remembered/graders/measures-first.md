---
type: llm
---

PASS if the answer says the agent's usage is measured right then, before the agent is chosen or any worker is started (the plugin's `scripts/agent-usage.sh`, or the agent's own `/usage`), and that the choice follows from that reading; and it does not treat the 2026-10-21 memory note as evidence (it is old; it may be mentioned only as something not relied on). It may say what happens when the measurement shows kiro spent (use claude if claude has room, say so) or when it cannot be measured (stop and say what blocks, who opens it, what was tried).
FAIL if it passes `--agent claude` (or keeps kiro) because of the memory note, chooses without measuring, or says it would measure only after the workers started.
