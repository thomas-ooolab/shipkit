---
description: "#30013: a generic LGTM that names no PR covers none; sign-off is per PR and pinned to the head sha."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

/pr AR-450, review loop. Two PRs: service-be (head aaa1111) and service-fe (head bbb2222). The reviewer bot answers only 'LGTM, looks good to me' and names no PR. How many PRs are signed off, and what does /pr do next?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
