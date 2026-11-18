---
description: "AR-683: a P3 that only touches a comment, a doc, a test name or an api.yml description is fixed in the same /assign round before sign-off (root docs in the root PR), no full review, never a follow-up."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running /pr's review loop for AR-683. The reviewer bot's verdict approves with comments: no P1, no P2, and two P3 findings. F-02: the comment on the interface `ReportRepository.IsManagerAuthorized`, the comment of `helper.RequireReportAccess` and the doc of `groupRepo.Delete` still describe the old rule (comments only, no behaviour change). F-03: the root repo's `docs/features/reports.md` does not state the new rule yet (markdown only). Both files may be outside the spec's allowlist. What do you do with F-02 and F-03, what do you post to the reviewer, how are the PRs marked, and what goes in the follow-up list?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
