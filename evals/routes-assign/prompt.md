---
description: "A user's plain request that /assign is for; the skill must be the one Claude picks."
tags: [routing]
max_turns: 8
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
---

The spec of AR-458 tags tasks in three submodules. Implement them in parallel with background agents, one per submodule, instead of one after the other.
