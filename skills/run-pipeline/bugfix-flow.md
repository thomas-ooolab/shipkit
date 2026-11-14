# run-pipeline · bug-fix flow

Read when `FLOW=bug` (Step 1). It replaces Steps 2–5 of `SKILL.md` for a defect: same rules (cite sources, never guess,
never merge, never edit code), different stages. Canonical order: `stages-bugfix.txt`.

## Flow
```
/bugfix <ticket> [<comment-id>] [--agent kiro]   triage, fix on the fix branch, /verify per concern, spec.md edited in place when the fix changes it
      ▼
/verify  +  /review-changes                       /verify only when the spec or plan changed; either order
      ▼
/pr <ticket> --bug
      ▼
/merge <ticket>                                   GATE — the user runs it
      ▼
/bump-submodule path@sha --closes <ticket>        only after a by-hand merge
```
No `/spec-from-ticket`, `/clarify`, `/plan-deep` and no design-recon: `/bugfix` keeps `spec.md` true itself (its Step 3.1b —
REQ text, Contracts, Plan edited in place, each change resting on a PO answer or a dated Jira decision) and proves each fixed
concern (`/verify --concern`, evidence under `.shipkit/evidence/<ticket>/`). Never dispatch those three from this flow.
**Spec changed** = `git diff origin/<target>...HEAD -U0 -- <SPEC>/spec.md` has a changed line outside `## Tasks` (the fix tasks
`/bugfix` appends there don't count). Then the requirements it changed are re-proved by a stand-alone `/verify --ticket <ticket> --req …`, as in the
standard flow, **scoped to what the fix changed**: `--req REQ-NNN …` = the ids on the changed lines outside `## Tasks`, plus the
`[REQ-NNN]` tag of each fix task the branch added there (`{fix`), plus the requirements that cite a changed `## Contracts` entry.
A change no requirement can be named for → no `--req` (the whole ticket), and the state line says so. Otherwise that stage is skipped.
No `spec.md` (`probe.sh state` → `SPEC=none`: a stand-alone bug ticket, where `/bugfix` fixes through a free-form `/assign` and its Step 1b is a no-op) → there is nothing to diff: the spec is unchanged and this stage is skipped.

## Derive state (Step 2 for a bug)
`probe.sh state <ticket>` plus the same Bitbucket PR lookup as Step 2, with `fix/<ticket>-` in place of `feat/<ticket>-` (keep `feat/` when the fix went onto the ticket's own unmerged feature branch).
**REQUIRED:** Read `${CLAUDE_PLUGIN_ROOT}/skills/run-pipeline/loop-rules.md` — failure classes, fixers, rounds and caps, PASS pinned to `HEAD`, `auto` advance; same rules as the standard flow.
| Stage | Passes when |
|---|---|
| **bugfix** | `.shipkit/bugfix-<ticket>.md` lists no real-defect concern without `verified:`; and the branch (`fix/<ticket>-*`, else the ticket's `feat/` branch) has commits beyond `origin/<target>`, or the state file is gone and `.shipkit/evidence/<ticket>/` holds the proof. A concern `/bugfix` holds (its round cap, a blocker) stays open and does not stop the others from shipping, but it blocks an auto-merge (`loop-rules.md` §5). The question `/bugfix` asks about it is class C: `Status: waiting-user` names the concern; the fixed concerns are not rolled back and the next pass continues with them |
| **verify** *(gate, only when the spec changed)* | spec unchanged (diff above is empty outside `## Tasks`) → skipped, `[x] … skipped: spec unchanged`; changed → the last `/verify` printed `verify: PASS` and its `passed @` line is current |
| **review** | the last `/review-changes` reported `0 blocking` and its `passed @` line is current |
| **prs** | a Bitbucket PR exists per affected submodule + parent (affected = has changes vs its default branch, as `/pr` Step 2 decides; a tagged submodule with no change is not waited on), `/pr` reported every one signed off (a `signed-off @` line per PR), and — when a spec exists — the verify PASS is current again after `/pr` (`loop-rules.md` §4; `SPEC=none` has no REQ to scope a re-verify by, so `/bugfix`'s own evidence stands and the stage notes `no re-verify: no spec`) |
| **merged** *(gate)* | all child PRs merged |
| **bump** | parent submodule refs point at merged shas; parent PR open/merged |

Audit line before any dispatch: `shipkit bug <ticket>: bugfix=<done|pending> concerns=<fixed/total> spec-changed=<yes|no> verify=<done|skipped|stale|pending> review=<done|stale|pending> prs=<n/m|unknown> merged=<yes|no|unknown> rounds=<used>/6`

## State file
`Status:`, `Next:`, the context rows (`PRs:`, `Evidence:`; the wait on the reporter is read from `.shipkit/bugfix-<ticket>.md` by the pane, so no `Poller:` line) and the optional `  - detail:` line under a stage are written as `SKILL.md` Step 3 says (rewritten after every stage and before every stop;
here `waiting-user` also covers a Jira comment that asks the reporter or the PO something and awaits the user's confirmation, and the reporter's reply — never a fixed-and-pushed note, whether it is not yet approved or skipped by the user: `/bugfix` announces that note once, and `/merge` sends the evidence).
`.shipkit/pipeline-<ticket>.md`, same line shape as the standard flow (the `/pipeline` pane reads `- [x] <id> <name>`), header `Flow: bug`:
```markdown
# Pipeline state — <ticket>
Flow: bug · Auto: <yes|no> · Updated: <ISO-8601>
Rounds: <used>/6
Status: <running|waiting-user|failed|done> · <what it waits on, or why it failed>
Next: <the single next action>
PRs: root=<pr url> <suffix>=<pr url>
Evidence: .shipkit/evidence/<ticket>/

## Stages
- [ ] 1 bugfix  — /bugfix <ticket> [<comment-id>] [--agent kiro]
  - detail: root  fix/<ticket>-<slug>
  - detail: <suffix>  <that submodule's fix branch>
- [ ] 2 verify  — /verify --ticket <ticket> --req <the changed REQs> --no-jira (only when the spec changed; else skipped: spec unchanged)
- [ ] 3 review  — /review-changes
- [ ] 4 prs     — /pr <ticket> --bug
- [ ] 5 merged  — GATE: /merge <ticket>
- [ ] 6 bump    — /bump-submodule only after a by-hand merge
```

## Run pending stages
- **Stage 1 — bugfix:** dispatch `/bugfix <ticket> [<comment-id>]` (add `--agent kiro` when the run was given it). It writes
  its own state and Jira comments, each one confirmed by the user; the reporter-wait loop is its own background poller and
  is **not** a gate here. Continue to Stage 2 once the stage table above reads complete. Every concern was a not-a-defect
  explanation, a PO decision or a hand-off to another owner (no commit beyond the target) → **stop**: "No fix to ship for <ticket> — `/bugfix` keeps waiting
  for the reporter; re-run `/run-pipeline <ticket> --bug` when it produced a fix." When a concern was handed off, the message also names each owner and ticket (`handed off: <concern> → <owner>, <ticket>`).
- **Stage 2 — verify** *(gate, only when the spec changed)*: `/verify --ticket <ticket> --req <REQ-NNN> … --no-jira` (the set above), otherwise exactly Stage 4.5 of `SKILL.md`
  (without `auto`, `FAILED` and `INCOMPLETE` stop the run; with `auto`, `FAILED` is class A of `loop-rules.md` — fix, re-run, in rounds — and `INCOMPLETE` stops; never waived). `--no-jira`: no evidence comment is drafted — in this flow `/bugfix`
  drafts the one Jira comment (Step 3.3, confirmed by the user before it posts), so this run adds no feature evidence draft; `/merge` sends the bug-fix table that `/bugfix`'s own `--concern` run wrote (`jira-comment-*.md`), as its evidence comment. Spec unchanged → mark `[x]` with `skipped: spec unchanged`; nothing is dispatched.
- **Stage 3 — review:** `/review-changes --ticket <ticket>`; success = `0 blocking`, write its `passed @` line. Blocking findings stop the run without `auto`; with `AUTO=true` they are class A (fix, re-run, in rounds).
- **Stage 4 — prs:** `/pr <ticket> --target <pr_target> --bug`; review loop on `/pr`'s own pollers. Without `auto` it stops at the open PRs; with `AUTO=true` it stays until `/pr` reports every PR signed off, then does the `signed-off @` and post-`/pr` re-verify bookkeeping of `loop-rules.md` §4. `--bug` makes `/pr` take the affected submodules from the fix's own git diff, never from the spec's `## Tasks` tags (the spec belongs to the feature already built).
- **Stage 5 — merged** *(gate)* and **Stage 6 — bump:** exactly Stages 6–7 of `SKILL.md` (with `auto`, `/merge` only under `loop-rules.md` §5 — precondition 3 reads `.shipkit/bugfix-<ticket>.md`).

A stage failure follows `SKILL.md`: `.shipkit/pipeline-failure-<ticket>.md`, `❌` in the state file, stop.

## Report
```
shipkit · bug <ticket> — <title>   [resumed at stage N]
Stages: 1✅ 2✅ 3✅ 4… 5… 6…
Fix:    <branch> · evidence <path(s)>
PRs:    <child PR urls + parent PR url, or "—">
Next:   <the single next action>
```
