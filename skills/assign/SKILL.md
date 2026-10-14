---
name: assign
description: "Use when a ticket's spec.md tags tasks across ≥2 submodules and they'd otherwise get implemented one submodule at a time — hands each submodule's allowlisted tasks to a parallel background agent (same kind as the running agent) so they implement concurrently, in dependency waves per the plan's Part order. Also delegates a single target or a free-form task (single-repo, no config, non-ticket args) to one agent. Trigger: /assign <jira-ticket | task>. Examples: \"/assign AR-450\", \"parallelize AR-458's implementation across submodules\", \"stop doing these submodules one at a time\""
argument-hint: "<jira-ticket | task text> [--only <submodule,...>] [--agent claude|kiro]"
---

# shipkit · assign

Fans out a ticket's per-submodule implementation tasks to parallel background agents (spawned like the running agent) instead of
working through submodules one at a time. Reads the tasks `/plan-deep` already wrote and grouped
per submodule; adds nothing to the plan itself.

> **Cite-sources rule.** Every submodule's "already in progress" / "not started" call traces to
> `probe.sh state` (branch dirty/unpushed), never assumed from a prior run's memory.
>
> **Never-guess rule.** In ticket mode, if `spec.md` has no `## Tasks` tagged with submodule targets,
> stop. Never invent a parallel split — one target runs as one target, not as a fake fan-out.
>
> **Forbidden language.** No "I think this pair is independent." Say "no Part order note pins these
> two — treating as parallel" / "confirmed dirty via probe.sh — skipping."

## Bounded scope
Implements code only (ticket mode reads the plan; free-form mode takes the task as given). Does **not** open PRs (`/pr`), review (`/review-changes`), bump submodule refs
(`/bump-submodule`), or write the plan (`/plan-deep`). If `spec.md` doesn't exist yet, stop: "Run
`/spec-from-ticket <ticket>` then `/plan-deep <ticket>` first."

## Write surface (the ONLY things written)
1. Code in each submodule, restricted to that submodule's task-tagged file paths.
2. One commit + push per submodule's feature branch (creates the branch if missing).
3. `specs/NNN-slug/spec.md` — check off `[x]` tasks the agent confirmed done (and git verifies).
4. `.shipkit/assign-<ticket>.md` — per-submodule wave/status log (Orca mode: plus each agent's terminal handle).
5. `.shipkit/assign-failure-<ticket>.md` — on any agent failure (submodule, error, recovery).
6. Orca mode only: one Orca terminal per submodule (`terminal create` / `send`) — never an Orca worktree or orchestration task.
**Forbidden side-effects:** never open/merge a PR; never touch the parent repo; never write outside
a submodule's own task allowlist; no force-push unless that submodule's branch was rebased.

---

## Dynamic context (injected)
```
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" resolve`
```
Pick the mode in Step 1. Neither a single-repo topology nor `SHIPKIT_CONFIG_EXISTS=0` stops the
run: delegation to an agent needs only a path and a brief. `/bootstrap` is required only for
**ticket mode on `meta-with-submodules`**, where the config's `submodules[]` is the only source of paths.

## Step 1 — Parse + pick mode
Tokenize `$ARGUMENTS`; strip `--only <a,b>` → `ONLY[]` (each must be in the config's
`submodules[].name`, else stop: "`<name>` isn't a configured submodule."); strip `--agent claude|kiro` →
`AGENT` (default `claude`, the running agent's own CLI; `kiro` runs `kiro-cli chat` and needs Orca mode).
- **Ticket mode** — exactly one ticket-shaped token (`AR-450`) **and** `meta-with-submodules` with a
  config: continue to Step 2. Single-repo topology + ticket token: one target (repo root), same
  flow with the spec's tasks as the brief.
- **Free-form mode** — args are not ticket-shaped (or no spec/config to read): one target = repo
  root (`git rev-parse --show-toplevel`), `BRIEF` = the args verbatim + the repo path + "run the
  repo's tests, commit, push the branch". Skip Steps 2–4 and 6's spec check-off; go to Step 5 with a
  single-target wave. Empty args → AskUserQuestion (Vietnamese) what to implement.
- Ticket token but `meta-with-submodules` and `SHIPKIT_CONFIG_EXISTS=0` → stop: "Run `/bootstrap` first."

## Step 2 — Load the plan (ticket mode)
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" state <TICKET>
```
`SPEC=none` → stop (see Bounded scope). Read `specs/NNN-slug/spec.md` in full. Parse `## Tasks`:
each `- [ ] T0NN [REQ-NNN] (<submodule>) {desc} — <file path>`. Group by `<submodule>`; drop any
submodule not in scope or excluded by `ONLY`. Zero groups → stop. **One group is fine** — it's a
single-target run (no waves to print). Read the **Fan-out**/**Part order** note if present
(e.g. "BE before FE").

## Step 3 — Build waves
- No Part order note → **one wave**: every remaining submodule, fully parallel.
- Part order note → order submodules into waves by the pinned sequence; a submodule the note
  doesn't mention joins wave 1 (nothing says it waits). Two submodules the note doesn't order
  relative to each other share a wave.
- Print the wave plan before dispatching anything:
  ```
  Wave 1 (parallel): ai-roleplay-be, ai-roleplay-voice
  Wave 2 (parallel): ai-roleplay
  ```

## Step 4 — Ground-truth skip check (per submodule, before its wave runs)
From the Step 2 probe: `dirty=yes` or `unpushed>0` on that submodule's `feat/<ticket>-*` branch means
work already started. Default: skip it (report "already in progress — skip", don't overwrite).
To force a re-run anyway, the user must say so explicitly — AskUserQuestion: "`<submodule>` already
has {dirty|unpushed} changes on its branch — re-run its agent anyway and let it continue from
there, or skip?" (`--only <name>` alone does not imply force.)

## Step 5 — Delegate each wave (parallel)
**Transport — pick once, before the first wave.** Resolve `ORCA` the way the `orca-cli` skill's stub says,
then run `ORCA worktree current --json`. It succeeds (the session is inside an Orca-managed worktree)
→ **Orca mode** (below). Anything else — no CLI, Orca not running, not an Orca worktree — → **Agent
mode**, except `--agent kiro`, which stops: "kiro runs only as an Orca terminal." Never `ORCA open` just to get Orca mode.

**Agent mode.** Dispatch every submodule left in the wave **in one message**: one `Agent` call each, `subagent_type`
`general-purpose` (the running agent's own kind), `run_in_background: true`, no model override, no
worktree isolation (each agent owns a distinct submodule); the brief tells it to work only inside `PATH`. No waiting
between submodules — this is the whole point. Each agent's final line must be exactly
`✅ implemented <path> (N/M tasks)` or `❌ <reason>`.
Per submodule, `PATH` = its path,
`NAME` = its name, and `BRIEF` is composed of (free-form mode: Step 1's `BRIEF` as-is, `NAME` = repo dir name):
- **Grounding:** read the submodule's `CLAUDE.md` + `docs/<service>.md` first; reuse existing
  patterns, don't invent structure.
- **Branch:** create `feat/<ticket>-<slug><suffix>` (config `suffix`) from the submodule's tracking
  `branch` (config) if missing; else continue on the existing one.
- **Objective + tasks:** only this submodule's checkbox items from `## Tasks`, each with its
  `REQ-NNN`, plus the absolute path of `spec.md`.
- **Allowlist:** only the file paths those tasks name — never write outside it; if a needed file
  isn't listed, **stop** and report the gap (don't widen the allowlist itself).
- **Discipline:** BE → OpenAPI-first (`api/api.yml` → `make gen` → domain → repo → handler); FE →
  BFF proxy + TanStack; Voice → Pipecat, staging-only.
- **Verify:** run the submodule's test command (Makefile `test` target → package-manager test
  script → `pytest`/`go test ./...`, first match). On failure, stop and report — don't push red.
- **Commit + push:** `git add <allowlisted paths>` (never `-A`); one commit; push the branch.

**Orca mode** (REQUIRED: load the `orca-cli` skill first). Same `BRIEF`, one agent per submodule, same
wave order — only the agent's home changes: a visible terminal in the current worktree instead of a hidden
`Agent`. For every submodule in the wave, do 1–3 before waiting on any of them:
1. `ORCA terminal create --worktree active --title <NAME> --command <AGENT command> --json` → keep the `handle`
   (`claude` → `claude`, `kiro` → `"kiro-cli chat"`; never `--trust-all-tools`). The agent shares this checkout and owns only its `PATH`, as in
   Agent mode — never `worktree create` (a second checkout `probe.sh` can't see) or `orchestration task-create`.
2. `ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json`; send only when
   `wait.satisfied` is true, else that submodule is `❌ agent did not start`.
3. `ORCA terminal send --terminal <handle> --text "<BRIEF>" --enter --wait-submit 10 --json`. Never resend on a
   receipt that only says `input_accepted`.
4. Then per handle `ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 1800000 --json` and
   `ORCA terminal read --terminal <handle> --json` for the agent's final `✅`/`❌` line. No such line (idle on
   a permission prompt, or timed out) → `❌ needs attention — terminal <handle>`: tell the user, and never
   answer a prompt on their behalf.
Leave terminals open so the user can read them; record the handles in the state file. Checkpoint with
`ORCA worktree set --worktree active --comment "assign <ticket>: wave N running (<names>)" --json`.

Wait for the whole wave to finish (a completion notification from every agent in it; Orca mode: step 4 for
every handle) before starting the next wave — a later wave may depend on what an earlier one just pushed (e.g. FE reading BE's freshly
generated types).

## Step 6 — Reconcile + report
Per agent's `✅`, check off its tasks `[x]` in `spec.md` (only the ones it confirmed — never assume
the rest of that submodule's tasks are done because one succeeded). Any `❌` → append to
`.shipkit/assign-failure-<ticket>.md` (submodule, error, recovery) and keep the other submodules'
results — one failure doesn't roll back siblings. Write `.shipkit/assign-<ticket>.md`:
```
# Assign state — <ticket>
Wave 1: ai-roleplay-be        ✅ 3/3 tasks   branch=feat/AR-450-rooms-be
        ai-roleplay-voice     ✅ 1/1 tasks   branch=feat/AR-450-rooms-voice
Wave 2: ai-roleplay           ❌ test failure — see assign-failure-AR-450.md
```
Report the same table to the user, then: "Run `/verify --ticket <ticket>` first — it proves each requirement on the running app (FE screenshot, BE data) — then `/pr <ticket>` to open PRs for the completed
submodules." (Failed ones need a fix-and-retry `/assign <ticket> --only <name>` first.)

## Gotchas
- **Parallel within a wave, sequential across waves — never the reverse.** The whole point is not
  waiting on submodule N to start submodule N+1 when nothing actually depends on it; don't collapse
  back to one-at-a-time inside a wave "to be safe."
- **A missing Part order note doesn't mean "ask the user which order."** No note = no known
  dependency = one wave, everything parallel. Only split waves on a note that's actually there.
- **Don't reuse a stale wave plan across retries.** A submodule fixed since the last failure may now
  be `dirty=yes` from that fix — re-probe (Step 2/4) every run, never cache wave membership.
- **Trust git, not the agent's last line.** Before checking off tasks, confirm via `probe.sh state` that
  the feature branch exists and is pushed (`unpushed=0`); otherwise record `❌ not pushed`.
- **This is not `/pr --implement`.** That flag lives inside `/pr`'s own PR-opening flow and only
  covers submodules not already PR'd. `/assign` runs standalone, any time, independent of PR state,
  and hands off to `/pr` afterward instead of opening PRs itself.
