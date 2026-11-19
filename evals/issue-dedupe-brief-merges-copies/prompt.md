---
description: "AR-678: a task adds method Release to the counter interface and three hand-written in-memory fakes already implement it. The coordinator greps every implementer before the brief and writes the task as 'merge into the shared one, add the missing accessor', with the shared file and callers in the allowlist from the start."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are the coordinator of `/assign AR-678` and are composing the BRIEF for service-be. The task from `spec.md`: `- [ ] T004 [REQ-004] (service-be) {add Release(ctx, key) to the Counter interface and call it on a rejected request} — pkg/ailimit/limiter.go`. Your grep of the code finds three hand-written in-memory implementations of that interface, all only used by tests: `fakeCounter` in `pkg/ailimit/limiter_test.go`, `memCounter` in `pkg/ginext/ai_limit_middleware_test.go`, and `ailimittest.Counter` in `pkg/ailimit/ailimittest/counter.go` (which has `Reserve` and `Inc` but no `Total()` accessor; `memCounter` and `fakeCounter` each re-implement the same map-and-mutex logic). What do you write as the task in the brief and what is in its allowlist? Which is the right way to give a worker this work, and what would the review say if the brief just said "add Release to each implementation"?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
