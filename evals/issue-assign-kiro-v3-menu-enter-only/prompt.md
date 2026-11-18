---
description: "/assign Orca mode: on kiro's V2/V3 menu the coordinator sends Enter only when the cursor is on 'Continue with V3'; any other option is the user's."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/assign, Orca mode, kiro worker. You created the warm terminal `term_k1` in this invocation with `kiro-cli chat --tui --trust-all-tools --v3`. You read its screen: "Kiro CLI 3.0 is here. The new V3 agent brings workflows…" and a menu with `❯ Continue with V3`, `Stay on V2, remind me later`, `Stay on V2, don't ask again`. What do you do with this screen? And if the cursor `❯` were on `Stay on V2, don't ask again` instead, what then?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
