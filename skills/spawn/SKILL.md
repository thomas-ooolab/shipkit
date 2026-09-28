---
name: spawn
description: "Use when a ticket's spec.md tags tasks across ≥2 submodules and they'd otherwise get implemented one submodule at a time — dispatches one background, worktree-isolated agent per submodule to implement its allowlisted tasks in parallel, in dependency waves per the plan's Part order. Trigger: /spawn <jira-ticket>. Examples: \"/spawn AR-450\", \"parallelize AR-458's implementation across submodules\", \"stop doing these submodules one at a time\""
argument-hint: "<jira-ticket> [--only <submodule,...>]"
---

# shipkit · spawn

Fans out a ticket's per-submodule implementation tasks to parallel background agents instead of
working through submodules one at a time. Reads the tasks `/plan-deep` already wrote and grouped
per submodule; adds nothing to the plan itself.

> **Cite-sources rule.** Every submodule's "already in progress" / "not started" call traces to
> `probe.sh state` (branch dirty/unpushed), never assumed from a prior run's memory.
>
> **Never-guess rule.** If `spec.md` has no `## Tasks` tagged with submodule targets, or fewer than 2
> submodules remain after filtering, stop — don't invent a parallel split.
>
> **Forbidden language.** No "I think this pair is independent." Say "no Part order note pins these
> two — treating as parallel" / "confirmed dirty via probe.sh — skipping."

## Bounded scope
Implements code only. Does **not** open PRs (`/pr`), review (`/review-changes`), bump submodule refs
(`/bump-submodule`), or write the plan (`/plan-deep`). If `spec.md` doesn't exist yet, stop: "Run
`/spec-from-ticket <ticket>` then `/plan-deep <ticket>` first."

## Write surface (the ONLY things written)
1. Code in each submodule, restricted to that submodule's task-tagged file paths.
2. One commit + push per submodule's feature branch (creates the branch if missing).
3. `specs/NNN-slug/spec.md` — check off `[x]` tasks the dispatched agent confirmed done.
4. `.shipkit/spawn-<ticket>.md` — per-submodule wave/status log.
5. `.shipkit/spawn-failure-<ticket>.md` — on any agent failure (submodule, error, recovery).
**Forbidden side-effects:** never open/merge a PR; never touch the parent repo; never write outside
a submodule's own task allowlist; no force-push unless that submodule's branch was rebased.

---

## Dynamic context (injected)
```
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" resolve`
```
If `SHIPKIT_CONFIG_EXISTS=0`, stop: "Run `/bootstrap` first." Single-repo topology → stop: "Only
one target — implement directly, `/spawn` needs ≥2 submodules to parallelize."

## Step 1 — Parse
Tokenize `$ARGUMENTS`: one ticket-shaped token → `TICKET`. `--only <a,b>` → `ONLY[]` (restrict to
named submodules; each must be in the config's `submodules[].name`, else stop: "`<name>` isn't a
configured submodule."). Missing/ambiguous ticket → AskUserQuestion, don't infer.

## Step 2 — Load the plan
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" state <TICKET>
```
`SPEC=none` → stop (see Bounded scope). Read `specs/NNN-slug/spec.md` in full. Parse `## Tasks`:
each `- [ ] T0NN [REQ-NNN] (<submodule>) {desc} — <file path>`. Group by `<submodule>`; drop any
submodule not in scope or excluded by `ONLY`. Fewer than 2 groups remain → stop (see Dynamic
context). Read the **Fan-out**/**Part order** note if present (e.g. "BE before FE").

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

## Step 5 — Spawn each wave (parallel, one message per wave)
For every submodule left in the wave, in **one message** (all `Agent` calls together — this is the
whole point, not one at a time), dispatch a background agent with `isolation: "worktree"` scoped to
that submodule's path. Compose the prompt with:
- **Grounding:** read the submodule's `CLAUDE.md` + `docs/<service>.md` first; reuse existing
  patterns, don't invent structure.
- **Branch:** create `feat/<ticket>-<slug><suffix>` (config `suffix`) from the submodule's tracking
  `branch` (config) if missing; else continue on the existing one.
- **Objective + tasks:** only this submodule's checkbox items from `## Tasks`, each with its
  `REQ-NNN`.
- **Allowlist:** only the file paths those tasks name — never write outside it; if a needed file
  isn't listed, **stop** and report the gap (don't widen the allowlist itself).
- **Discipline:** BE → OpenAPI-first (`api/api.yml` → `make gen` → domain → repo → handler); FE →
  BFF proxy + TanStack; Voice → Pipecat, staging-only.
- **Verify:** run the submodule's test command (Makefile `test` target → package-manager test
  script → `pytest`/`go test ./...`, first match). On failure, stop and report — don't push red.
- **Commit + push:** `git add <allowlisted paths>` (never `-A`); one commit; push the branch. Report
  `✅ implemented <path> (N/M tasks)` or `❌ <reason>`.
Wait for the whole wave to finish (success or failure on every agent in it) before starting the next
wave — a later wave may depend on what an earlier one just pushed (e.g. FE reading BE's freshly
generated types).

## Step 6 — Reconcile + report
Per agent's `✅`, check off its tasks `[x]` in `spec.md` (only the ones it confirmed — never assume
the rest of that submodule's tasks are done because one succeeded). Any `❌` → append to
`.shipkit/spawn-failure-<ticket>.md` (submodule, error, recovery) and keep the other submodules'
results — one failure doesn't roll back siblings. Write `.shipkit/spawn-<ticket>.md`:
```
# Spawn state — <ticket>
Wave 1: ai-roleplay-be        ✅ 3/3 tasks   branch=feat/AR-450-rooms-be
        ai-roleplay-voice     ✅ 1/1 tasks   branch=feat/AR-450-rooms-voice
Wave 2: ai-roleplay           ❌ test failure — see spawn-failure-AR-450.md
```
Report the same table to the user, then: "Run `/pr <ticket>` next to open PRs for the completed
submodules." (Failed ones need a fix-and-retry `/spawn <ticket> --only <name>` first.)

## Gotchas
- **Parallel within a wave, sequential across waves — never the reverse.** The whole point is not
  waiting on submodule N to start submodule N+1 when nothing actually depends on it; don't collapse
  back to one-at-a-time inside a wave "to be safe."
- **A missing Part order note doesn't mean "ask the user which order."** No note = no known
  dependency = one wave, everything parallel. Only split waves on a note that's actually there.
- **Don't reuse a stale wave plan across retries.** A submodule fixed since the last failure may now
  be `dirty=yes` from that fix — re-probe (Step 2/4) every run, never cache wave membership.
- **This is not `/pr --implement`.** That flag lives inside `/pr`'s own PR-opening flow and only
  covers submodules not already PR'd. `/spawn` runs standalone, any time, independent of PR state,
  and hands off to `/pr` afterward instead of opening PRs itself.
