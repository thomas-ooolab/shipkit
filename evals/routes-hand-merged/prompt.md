---
description: "A user's plain request that /bump-submodule is for; the skill must be the one Claude picks."
tags: [routing]
max_turns: 8
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
---

I merged the child PRs of AR-450 by hand. Bump the parent repo's submodule pointers to the merged commits service-be@a1b2c3d and service-fe@e4f5a6b and update the parent PR.
