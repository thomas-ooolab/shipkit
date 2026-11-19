---
type: llm
---

PASS if the answer makes the task "merge the hand-written copies into the shared `ailimittest.Counter`, adding the accessor it lacks (`Total()`)" and not "add `Release` to each copy", and puts the shared file (`pkg/ailimit/ailimittest/counter.go`) and the files that hold the copies it replaces (`limiter_test.go`, `ai_limit_middleware_test.go`) in the allowlist from the start, each named with the task that needs it.
FAIL if the brief says to add `Release` to each of the three implementations, lists only `pkg/ailimit/limiter.go` as the allowlist, or leaves the shared file and callers for a later widening.
