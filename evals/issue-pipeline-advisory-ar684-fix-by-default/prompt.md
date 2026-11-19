---
description: "AR-684 (bug flow, no spec): review reports 0 blocking and 12 raw advisory findings that are 11 distinct problems (two pairs merge, one compound finding splits); the pass dedupes across reviewers, hands the fixer everything but design/schema/rollout, fixes call sites outside the diff, counts incomplete docs and a duplicated test helper, takes the no-op variant of the risky one, and every reason left is checked in that turn."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/run-pipeline AR-684 --bug auto` (a stand-alone bug ticket: `probe.sh state` says `SPEC=none`, so there is no spec and no allowlist). Stage 3, `/review-changes --ticket AR-684`, just returned `0 blocking, 12 advisory` from the three reviewers. The findings:

1. (style) `newDeliverer(..., repos ...repository.ReportRunRepository)` takes a variadic as an optional argument; a caller that forgets it silently disables the delivered-key dedupe. (2) (correctness) the same variadic parameter, worded differently. The fix is to make it required: the production caller already passes it, and 16 test call sites in `deliver_test.go` and `deliver_owner_access_test.go` do not (both files are outside the branch diff).
3. (style) the doc comment of `Deliver` does not say that it skips the pairs already in `run.DeliveredKeys`, records each success, or returns a "delivered but not recorded" error entry.
4. (style) the delivered-key format `<membershipID>:<channel>` is built inline and documented nowhere.
5. (style) the new test helper `newMockRunnelDB` hand-builds sqlmock + gorm; `pkg/db.CreateMock` already does it.
6. (style) `snapshotBytes, err := json.Marshal(snapshot)` in an `else` block shadows the outer `err`; every branch returns on error.
7. (infra) `workers/CLAUDE.md` still says nothing about idempotent redelivery or that `FetchJob` is now a transaction with SKIP LOCKED.
8. (style) in `Deliver` the delivered set lives in a local map, an in-place append to `run.DeliveredKeys` and the DB column, and the `deliveryError{...}` literal is written twice. A reviewer note adds: "a committed test may reuse the run pointer, so check before dropping the append".
9. (correctness) and 10. (infra) a dependency whose parent failed loops forever (the same problem, raised twice).
11. (infra) a new `runnel_rows(created_at)` index is missing (a migration).
12. (infra) the runs in flight resend once at the deploy (a rollout note).

The recorded `Rounds:` is `2/6`. What do you do next, in order, and what does the final report say about the advisories? When you leave an advisory, say what its reason rests on.

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
