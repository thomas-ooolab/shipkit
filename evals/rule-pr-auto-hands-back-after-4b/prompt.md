---
description: "AR-678: /pr --auto fixes the correctness item, defers the nits and gives control back instead of stopping."
tags: [rules]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/pr AR-478 --auto, review loop at step 4b. The reviewer's last round left four items: one P3 that is a correctness error (a case that returns the wrong total), and three wording and test-hygiene nits. No P1 or P2, no open question for the PO. What does /pr do next?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
