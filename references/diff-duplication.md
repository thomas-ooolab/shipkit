# Duplication the PR's own diff makes or multiplies: merge it, never defer it

**What it is.** The diff edits two or more hand-written copies of the same fake, helper, constant or logic: a method added to each of three in-memory fake
counters (AR-678: `fakeCounter`, `memCounter`, `ailimittest.Counter`). The cause of the duplication is the PR itself, so the remark about it is **dedupe**, not
"test hygiene" and not a follow-up. Duplication the PR does not touch is not covered here.

1. **Name it.** The style reviewer (`agents/style-docs-reviewer.md`) and the PR reviewer's remark are read for it: a finding that says several copies carries
   the number and the places (`dedupe: 3 hand-written in-memory counters, each edited by this diff: <file:line>, <file:line>, <file:line>`).
2. **Brief it right, before the work.** When a task adds a method to an interface or a type, the coordinator greps **every implementer first**, fakes in `*_test.go`
   and mocks included, before writing the brief. Two or more hand-written copies of the same logic make the task "merge them into the shared one (add the accessor it
   lacks)", never "add the method to each copy". The shared file and the places that call it are in the allowlist from the start, each named with the task that needs it
   (`/assign` Step 5, *Allowlist*; `/bugfix` Step 3.1).
3. **Fix it in the same round** (`/pr` step 4b; `/run-pipeline` `loop-rules.md` §12): merge every copy into the shared one (add the missing accessor to it, switch the callers, delete
   the copies), then run the tests of the packages changed. It changes no behaviour, so the shared file and the callers may lie outside the allowlist the earlier worker had:
   widening it here is right, not a silent widening. The task is appended to `spec.md` `## Tasks` with those paths (so the allowlist and `/review-changes`'s drift check stay
   true), and the brief names why each file is added. It is never put on a follow-up list.
4. **The one exception: a copy that cannot join.** An import cycle is the usual cause (a test in package `x` cannot import the helper package `xtest` that imports `x`). Check
   it by building or vetting that test package (`go vet`, `go build`, `tsc`), never assume it. A copy that cannot join stays, with **one** comment at it saying why; the other copies still merge.
5. **A claimed consequence that the PR's own build disproves is answered, not deferred.** When the reviewer says the duplication risks a compile error or a failing test and
   the PR's `go build` / tests / `tsc` passed, reply `not correct` with that run as the evidence (command and result), as a *Not an issue* line. A false claim is never
   part of the reason for a follow-up.

Evals: `evals/issue-dedupe-brief-merges-copies`, `evals/issue-dedupe-pr-remark-not-followup`.
