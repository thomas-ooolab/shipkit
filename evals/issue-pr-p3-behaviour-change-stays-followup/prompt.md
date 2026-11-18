---
description: "AR-683: a P3 that changes behaviour, needs a product decision or is unclear is not a nit: it goes to the follow-up list; the comment-only P3 in the same verdict is still fixed."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running /pr's review loop for AR-683. The reviewer bot's verdict approves with comments: no P1, no P2, three P3 findings. F-01: the list endpoint returns at most 50 reports and the bot suggests paging; adding it changes the API's behaviour and the ticket does not say what the page size should be. F-02: a comment on `helper.RequireReportAccess` still describes the old rule (comment only). F-03: the bot is unsure whether an empty `groupId` should be rejected or treated as "all groups"; the spec is silent. What do you do with each finding and what goes in the follow-up list?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
