# run-pipeline · pass, loop and stop rules

Read by `SKILL.md` Step 2 (both flows). The stage tables in `SKILL.md` and `bugfix-flow.md` say **when a stage passes**; this file
says what the orchestrator does when it does not, and when it stops. The orchestrator itself never edits code: every fix is a
dispatched skill.

## 1. Three failure classes

| Class | Examples | The orchestrator |
|---|---|---|
| **A · a skill can fix it** | `review` blocking findings; `verify` FAILED; `plan` with blocking review findings; `spec` REQ without a source; `implement` tasks unchecked (`AUTO` only) | dispatches the fixer from §2, re-runs the **same** stage — one **round** |
| **B · waiting on others** | open questions (the PO); `/pr`'s reviewer verdict; Bitbucket pipelines; the reporter's reply; a Jira/Slack draft that waits for the user's approval | `Status: waiting-user · <who or what it waits on>`, stops; the dispatched skill's own poller keeps running. Not a round |
| **C · needs a decision** | `verify` INCOMPLETE; a plan with `[UNVERIFIED …]` refs or tasks `blocked on OQ-N`; a missing mockup; a merge precondition of §5 that fails; any question a dispatched skill asks the user | `Status: waiting-user · <the concrete reason>`, stops at once. Not a round |

Only class A has rounds. An approval a dispatched skill needs (every Jira and Slack post) stays the user's: class B.
A failure that meets two classes is the higher one: C over A (a plan with blocking findings **and** a task `blocked on OQ-N` stops, it is not re-dispatched).
Without `auto` a class A failure is a stop like a class C one. Every stop in this file writes `Status: waiting-user`; `failed` is only for a dispatched command that errored (`SKILL.md`, "On any stage failure").

## 2. Fixers (class A)

| Stage | Fixer | Re-run |
|---|---|---|
| spec | `/spec-from-ticket <ticket>` | the spec predicate |
| plan | `/plan-deep --ticket <ticket> --auto` (it caps its own review passes at 2; one dispatch is one round) | the plan predicate |
| implement (`AUTO`) | `/assign <ticket> [--agent kiro]` | the implement predicate |
| review, verify (standard) | per submodule with a finding or a failed REQ: `cd` into it, `/assign "<brief>" --continue --no-push` (the brief quotes the blocking findings, or the failed REQ ids with `/verify`'s failure text, plus "fix only these, run the tests of the files you changed (`${CLAUDE_PLUGIN_ROOT}/references/scoped-tests.md`), commit, never push") | the **whole** stage again (`/review-changes --ticket`, `/verify --ticket`) |
| review, verify (bug) | the same | the same; `/verify` keeps its `--req` scope from `bugfix-flow.md` |
| bugfix (bug flow) | none — `/bugfix` loops itself (3 rounds per concern, its Step 3.1) | the bugfix predicate |
| prs | none — `/pr` loops itself (`loop.max_rounds`, per PR in `--per-pr`) | `/pr`'s own end |

A failed REQ goes to the submodules of its `## Tasks` lines (`[REQ-NNN] (<submodule>)`); with no such line, to every repo whose branch diff is not empty. A review finding goes to its own `submodule`.

Rounds spent **inside** `/pr`, `/plan-deep`, `/clarify`, `/assign` and `/bugfix` are theirs and are never counted again here. The
`/assign` brief goes to a coordinator that already holds the task's context; the orchestrator adds no code and no spec task.

## 3. Counting, progress, stop

- **Round** = one fixer dispatch, then the re-run of the same stage.
- **Caps:** 3 rounds per stage; 6 rounds per ticket. The stage counter restarts when the stage passes; the ticket counter never does.
- **Signature** of a failing run, read from that run's own output: `verify` → the failed REQ ids, sorted; `review` → the blocking count and the
  sorted `<submodule>/<file>` of its blocking findings (findings carry no id); `plan` → the blocking count, the sorted titles of the blocking findings as `/plan-deep` printed them, and the sorted `[UNVERIFIED]` refs;
  `implement` → the unchecked task ids; `spec` → the REQ ids without a source.
- **Stop at once** when a round's re-run has the same signature as the run before it: the fix did not move anything, so rounds 2 and 3 are not spent. A signature that
  differs in any way (a REQ gone, a REQ new) is progress for this test; only the caps end such a loop. When the same-signature stop and a cap coincide, the reason written is `no progress`.
- **Stop** when a stage has used its 3 rounds and still fails, or the ticket has used its 6.
- **Where it lives** (`.shipkit/pipeline-<ticket>.md`; the pane shows these lines as written): header `Rounds: <used>/6`; under the stage
  `  - detail: round <k>/3 · <stage> <signature>` (the signature is that of the latest run, the re-run that came back; k = fixes done, so the line first appears with k = 1 after the first fixer returns; it stays after a stop as the record and is removed when the stage passes). A stop writes
  `Status: waiting-user · <reason>` with one of `no progress: same failures after one round` / `<stage>: 3 rounds used` /
  `ticket: 6 rounds used`, a `Blocker: <stage id>: <reason>` header line, and `.shipkit/pipeline-failure-<ticket>.md` with every
  round's signature; a stop without `auto`, or a class B/C stop, writes `Status:` and `Next:` only. The stage stays `[ ]` — a loop stop is not `❌`, which is for a dispatched command that errored. Never put ⚠️ or ⬆️ on these lines (the pane reads them as a warning).

## 4. A PASS is pinned to the code it saw

- At each `review` and `verify` PASS write `  - detail: passed @ root=<sha7> <suffix>=<sha7> …` — `git -C <repo> rev-parse --short HEAD` of the parent and
  every affected submodule, read in that turn.
- A PASS is **current** only while every recorded sha equals that repo's `HEAD` now. Any code change (a fix round, a `/pr` fix round, a rebase) makes the
  earlier `review` and `verify` PASS **stale**: remove its `passed @` line and run it again, from the earliest stale stage in `SKILL.md`'s stage order (review, then verify; the failing stage's own re-run is one of them). A re-run of a stale PASS is not a round.
  This holds up to the moment `/pr` is dispatched. Commits made inside `/pr`'s own loop are reviewed by its reviewer, so they never make the `review` PASS stale; they only
  make the `verify` PASS stale (next bullet).
- **After `/pr` finishes** (its own loop may have pushed fixes), if a `verify` sha differs from `HEAD`: run `/verify --ticket <ticket> --req <REQ-NNN> … --no-jira` for the
  requirements whose `## Tasks` file paths (repo-relative, as the task lines write them) intersect `git diff <recorded sha>..HEAD --name-only` in any repo — one dispatch, the union of the ids over every repo that moved
  (a change in any repo that no requirement can be named for → no `--req`, the whole ticket). PASS → rewrite the verify `passed @` shas to `HEAD` with the note `scoped re-verify: REQ-…`; FAILED → class A like any `verify` failure.
  `/review-changes` does not run again here: the reviewer's loop was the review.
- When `/pr` reports done, write per PR `  - detail: signed-off @ <PR id> <head sha7>` (the PR's head, read from Bitbucket that turn). A commit that `/pr` pushed
  in its severity stop (nit fixes, "no re-review by design") is already in that head, so it is accepted; a head that moves **after** this line is not.

## 5. Auto-advance (`AUTO=true` only)

Without `auto` the `implement` and `merged` stages stop as `SKILL.md` Step 4 says. With `auto`:

- **implement** — the predicate fails because tasks are unchecked: dispatch the fixer of §2 (round 1 of the stage, no stop); it passes → go on to `review`.
- **merged** — dispatch `/merge <ticket>` only when **every** line holds, each read in that turn. One that fails is class C: stop and name it.
  1. every child PR's head sha equals its `signed-off @` line;
  2. the `verify` PASS is current (§4, including the re-verify after `/pr`), the `review` PASS was current when `/pr` was dispatched, and the newest `.shipkit/evidence/<ticket>/jira-comment-*.md` exists;
  3. `.shipkit/bugfix-<ticket>.md` is absent, or every concern in it is `[x]`;
  4. `python3 -I "${CLAUDE_PLUGIN_ROOT}/hooks/after-hours-push-guard.py" --minutes-left` prints at least 30 — `/merge`'s root bump needs a `git push`, and a merge cut in two by the push window leaves the children merged and the root not.
  `/merge` still asks only on a problem (its own Steps 3–5); that question is class C.
- Never `auto`: the clarify gate, any Jira/Slack post, `INCOMPLETE`, a failed precondition above. A concern `/bugfix` holds does not stop the stages before the merge
  (the fixed concerns still ship through review, verify and `/pr`); it stops the merge through precondition 3.
