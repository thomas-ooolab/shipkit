# run-pipeline · bug-fix flow

Read when `FLOW=bug` (Step 1). It replaces Steps 2–5 of `SKILL.md` for a defect: same rules (cite sources, never guess,
never merge, never edit code), different stages. Canonical order: `stages-bugfix.txt`.

## Flow
```
/bugfix <ticket> [<comment-id>] [--agent kiro]   triage, fix on the fix branch, /verify per concern, spec.md edited in place when the fix changes it
      ▼
/verify  +  /review-changes                       /verify only when the spec or plan changed; either order
      ▼
/pr
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

## Derive state (Step 2 for a bug)
`probe.sh state <ticket>` plus the same Bitbucket PR lookup as Step 2, with `fix/<ticket>-` in place of `feat/<ticket>-` (keep `feat/` when the fix went onto the ticket's own unmerged feature branch).
| Stage | Complete when |
|---|---|
| **bugfix** | `.shipkit/bugfix-<ticket>.md` lists no real-defect concern without `verified:`; and the branch (`fix/<ticket>-*`, else the ticket's `feat/` branch) has commits beyond `origin/<target>`, or the state file is gone and `.shipkit/evidence/<ticket>/` holds the proof |
| **verify** *(gate, only when the spec changed)* | spec unchanged (diff above is empty outside `## Tasks`) → skipped, `[x] … skipped: spec unchanged`; changed → `/verify` reported PASS (state file `[x]`) |
| **review** | `/review-changes` has run (state file marks it `[x]`) |
| **prs** | a Bitbucket PR exists per affected submodule + parent |
| **merged** *(external gate)* | all child PRs merged |
| **bump** | parent submodule refs point at merged shas; parent PR open/merged |

Audit line before any dispatch: `shipkit bug <ticket>: bugfix=<done|pending> concerns=<fixed/total> spec-changed=<yes|no> verify=<done|skipped|pending> review=<done|pending> prs=<n/m|unknown> merged=<yes|no|unknown>`

## State file
`Status:`, `Next:`, the context rows (`Branch:`, `PRs:`, `Evidence:`, `Poller:` — here `Poller:` reads `.shipkit/bugfix-<ticket>.md`'s `silent_ticks`) and the optional `  - detail:` line under a stage are written as `SKILL.md` Step 3 says (rewritten after every stage and before every stop;
here `waiting-user` also covers a Jira comment awaiting the user's confirmation and the reporter's reply).
`.shipkit/pipeline-<ticket>.md`, same line shape as the standard flow (the `/pipeline` pane reads `- [x] <id> <name>`), header `Flow: bug`:
```markdown
# Pipeline state — <ticket>
Flow: bug · Auto: <yes|no> · Updated: <ISO-8601>
Status: <running|waiting-user|failed|done> · <what it waits on, or why it failed>
Next: <the single next action>
Branch: fix/<ticket>-<slug>
PRs: <pr url> <pr url>
Evidence: .shipkit/evidence/<ticket>/
Poller: <the reporter's reply, silent <n>>

## Stages
- [ ] 1 bugfix  — /bugfix <ticket> [<comment-id>] [--agent kiro]
- [ ] 2 verify  — /verify --ticket <ticket> --req <the changed REQs> --no-jira (only when the spec changed; else skipped: spec unchanged)
- [ ] 3 review  — /review-changes
- [ ] 4 prs     — /pr
- [ ] 5 merged  — GATE: /merge <ticket>
- [ ] 6 bump    — /bump-submodule only after a by-hand merge
```

## Run pending stages
- **Stage 1 — bugfix:** dispatch `/bugfix <ticket> [<comment-id>]` (add `--agent kiro` when the run was given it). It writes
  its own state and Jira comments, each one confirmed by the user; the reporter-wait loop is its own background poller and
  is **not** a gate here. Continue to Stage 2 once the stage table above reads complete. Every concern was a not-a-defect
  explanation or a PO decision (no commit beyond the target) → **stop**: "No fix to ship for <ticket> — `/bugfix` keeps waiting
  for the reporter; re-run `/run-pipeline <ticket> --bug` when it produced a fix."
- **Stage 2 — verify** *(gate, only when the spec changed)*: `/verify --ticket <ticket> --req <REQ-NNN> … --no-jira` (the set above), otherwise exactly Stage 4.5 of `SKILL.md`
  (`FAILED` / `INCOMPLETE` stop the run, never waived in `AUTO=true`). `--no-jira`: no evidence comment is drafted — in this flow `/bugfix`
  drafts the one Jira comment (Step 3.3, confirmed by the user before it posts), so `/merge` finds no `jira-comment.md` and sends nothing. Spec unchanged → mark `[x]` with `skipped: spec unchanged`; nothing is dispatched.
- **Stage 3 — review:** `/review-changes --ticket <ticket>`; a blocking ⚠️ stops the run (`AUTO=true` surfaces, continues only if non-blocking).
- **Stage 4 — prs:** `/pr <ticket> --target <pr_target>`; stops at the open PRs, review loop on `/pr`'s own pollers.
- **Stage 5 — merged** *(gate)* and **Stage 6 — bump:** exactly Stages 6–7 of `SKILL.md`.

A stage failure follows `SKILL.md`: `.shipkit/pipeline-failure-<ticket>.md`, `❌` in the state file, stop.

## Report
```
shipkit · bug <ticket> — <title>   [resumed at stage N]
Stages: 1✅ 2✅ 3✅ 4… 5… 6…
Fix:    <branch> · evidence <path(s)>
PRs:    <child PR urls + parent PR url, or "—">
Next:   <the single next action>
```
