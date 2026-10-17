# run-pipeline · bug-fix flow

Read when `FLOW=bug` (Step 1). It replaces Steps 2–5 of `SKILL.md` for a defect: same rules (cite sources, never guess,
never merge, never edit code), different stages. Canonical order: `stages-bugfix.txt`.

## Flow
```
/bugfix <ticket> [<comment-id>] [--agent kiro]   triage, fix on the fix branch, /verify per concern
      ▼
/review-changes
      ▼
/pr
      ▼
/merge <ticket>                                   GATE — the user runs it
      ▼
/bump-submodule path@sha --closes <ticket>        only after a by-hand merge
```
No `/spec-from-ticket`, `/clarify`, `/plan-deep`, no design-recon and no stand-alone `/verify`: `/bugfix` proves each fixed
concern itself (`/verify --concern`, evidence under `.shipkit/evidence/<ticket>/`). Never dispatch them from this flow.

## Derive state (Step 2 for a bug)
`probe.sh state <ticket>` plus the same Bitbucket PR lookup as Step 2, with `fix/<ticket>-` in place of `feat/<ticket>-` (keep `feat/` when the fix went onto the ticket's own unmerged feature branch).
| Stage | Complete when |
|---|---|
| **bugfix** | `.shipkit/bugfix-<ticket>.md` lists no real-defect concern without `verified:`; and the branch (`fix/<ticket>-*`, else the ticket's `feat/` branch) has commits beyond `origin/<target>`, or the state file is gone and `.shipkit/evidence/<ticket>/` holds the proof |
| **review** | `/review-changes` has run (state file marks it `[x]`) |
| **prs** | a Bitbucket PR exists per affected submodule + parent |
| **merged** *(external gate)* | all child PRs merged |
| **bump** | parent submodule refs point at merged shas; parent PR open/merged |

Audit line before any dispatch: `shipkit bug <ticket>: bugfix=<done|pending> concerns=<fixed/total> review=<done|pending> prs=<n/m|unknown> merged=<yes|no|unknown>`

## State file
`.shipkit/pipeline-<ticket>.md`, same line shape as the feature flow (the `/pipeline` pane reads `- [x] <id> <name>`), header `Flow: bug`:
```markdown
# Pipeline state — <ticket>
Flow: bug · Branch: fix/<ticket>-<slug> · Auto: <yes|no> · Updated: <ISO-8601>

## Stages
- [ ] 1 bugfix  — /bugfix <ticket> [<comment-id>] [--agent kiro]
- [ ] 2 review  — /review-changes
- [ ] 3 prs     — /pr
- [ ] 4 merged  — GATE: /merge <ticket>
- [ ] 5 bump    — /bump-submodule only after a by-hand merge
```

## Run pending stages
- **Stage 1 — bugfix:** dispatch `/bugfix <ticket> [<comment-id>]` (add `--agent kiro` when the run was given it). It writes
  its own state and Jira comments, each one confirmed by the user; the reporter-wait loop is its own background poller and
  is **not** a gate here. Continue to Stage 2 once the stage table above reads complete. Every concern was a not-a-defect
  explanation or a PO decision (no commit beyond the target) → **stop**: "No fix to ship for <ticket> — `/bugfix` keeps waiting
  for the reporter; re-run `/run-pipeline <ticket> --bug` when it produced a fix."
- **Stage 2 — review:** `/review-changes --ticket <ticket>`; a blocking ⚠️ stops the run (`AUTO=true` surfaces, continues only if non-blocking).
- **Stage 3 — prs:** `/pr <ticket> --target <pr_target>`; stops at the open PRs, review loop on `/pr`'s own pollers.
- **Stage 4 — merged** *(gate)* and **Stage 5 — bump:** exactly Stages 6–7 of `SKILL.md`.

A stage failure follows `SKILL.md`: `.shipkit/pipeline-failure-<ticket>.md`, `❌` in the state file, stop.

## Report
```
shipkit · bug <ticket> — <title>   [resumed at stage N]
Stages: 1✅ 2✅ 3… 4… 5…
Fix:    <branch> · evidence <path(s)>
PRs:    <child PR urls + parent PR url, or "—">
Next:   <the single next action>
```
