---
description: "AR-678 (bug flow): review reports 0 blocking and 13 advisory; the coordinator fixes the stale-comment, wrong-REQ-ID and duplicate-code ones in one /assign pass, reports the rest, re-runs the review (not a round), with or without auto."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/run-pipeline AR-678 --bug` (no `auto`) and Stage 3, `/review-changes --ticket AR-678`, just returned `0 blocking, 13 advisory across 1 submodules`. The advisories: (1) to (5) a comment, the spec sentence and a test assertion message still describe the old Peek-then-count mechanism after the change to Reserve; (6) and (7) a test cites REQ-003 where it checks REQ-004; (8) the function that tests for the limit error is written twice, in two files the branch diff already changes; (9) the fake counter is copied into three test files; (10) "consider a token bucket instead of a fixed window" (a design opinion); (11) "watch the Reserve latency after the rollout" (a rollout note); (12) "should the limit be per workspace or per user?" (needs the PO); (13) "rename the response field `retry_after` in `api/api.yml`" (changes the API contract). The recorded `Rounds:` is `1/6`. What do you do next, in order, and what does the final report say about the 13 advisories?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
