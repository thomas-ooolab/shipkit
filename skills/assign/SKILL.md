---
name: assign
description: "Use when a ticket's spec.md tags tasks across ≥2 submodules and they would otherwise be implemented one submodule at a time, or when a single target or free-form task should be handed to a background agent. Trigger: /assign <jira-ticket | task> [--only <submodule,...>] [--agent claude|kiro] [--no-push]. Examples: \"/assign AR-450\", \"parallelize AR-458's implementation across submodules\""
argument-hint: "<jira-ticket | task text> [--only <submodule,...>] [--agent claude|kiro] [--no-push]"
---

# shipkit · assign

Fans out a ticket's per-submodule implementation tasks to parallel background agents (kiro terminals by default, claude as fallback) instead of
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
2. One commit per submodule's feature branch, made by the worker (creates the branch if missing). **Workers never push.** The
   coordinator — this session — pushes the branch only after it accepts the commit (*Accept, then push* in Step 5), and not at
   all with `--no-push`.
3. `specs/NNN-slug/spec.md` — check off `[x]` tasks the agent confirmed done (and git verifies).
4. `.shipkit/assign-<ticket>.md` — per-submodule wave/status log (Orca mode: plus each agent's terminal handle).
5. `.shipkit/assign-failure-<ticket>.md` — on any agent failure (submodule, error, recovery).
6. Orca mode (kiro or claude workers): one `orchestration run-create` per invocation, then `worker-start`, `check`, `reply`, `worker-retain` / `worker-release` / `worker-stop` / `worker-abandon` (the last two only on positive proof the agent exited) — never an Orca worktree, `dispatch --inject`, `orchestration reset`, or a brief sent with `terminal send`.
**Forbidden side-effects:** never open/merge a PR; never touch the parent repo; never write outside
a submodule's own task allowlist; no push by a worker, ever; no force-push unless that submodule's branch was rebased.

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
`submodules[].name`, else stop: "`<name>` isn't a configured submodule."); strip `--no-push` → `NO_PUSH` (the coordinator accepts the commits but pushes nothing; the caller pushes, e.g. `/bugfix` after `/verify` passes); strip `--agent claude|kiro` →
`AGENT` (default `kiro` in Orca mode, `claude` in Agent mode — Step 5 picks the mode; an explicit flag always wins. In Orca mode both agents are Orca-supervised workers (`worker-start`; `claude` with `--model sonnet --effort medium`); in Agent mode `claude` is a background `Agent` call. `kiro` runs as an Orca-supervised worker (its tools are trusted, so the BRIEF's Guard is its only brake) and needs Orca mode).
- **Ticket mode** — exactly one ticket-shaped token (`AR-450`) **and** `meta-with-submodules` with a
  config: continue to Step 2. Single-repo topology + ticket token: one target (repo root), same
  flow with the spec's tasks as the brief.
- **Free-form mode** — args are not ticket-shaped (or no spec/config to read): one target = repo
  root (`git rev-parse --show-toplevel`), `BRIEF` = the args verbatim + the repo path + "run the
  repo's tests for the files it changes (not the whole suite: `${CLAUDE_PLUGIN_ROOT}/references/scoped-tests.md`) and commit (never push)". Skip Steps 2–4 and 6's spec check-off; go to Step 5 with a
  single-target wave. Empty args → AskUserQuestion (in the user's language) what to implement.
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
  Wave 1 (parallel): <submodule-a>, <submodule-b>
  Wave 2 (parallel): <submodule-c>
  ```

## Step 4 — Ground-truth skip check (per submodule, before its wave runs)
From the Step 2 probe: `dirty=yes` or `unpushed>0` on that submodule's `feat/<ticket>-*` (or `fix/<ticket>-*`) branch means
work already started. Default: skip it (report "already in progress — skip", don't overwrite).
To force a re-run anyway, the user must say so explicitly — AskUserQuestion: "`<submodule>` already
has {dirty|unpushed} changes on its branch — re-run its agent anyway and let it continue from
there, or skip?" (`--only <name>` alone does not imply force.)

## Step 4b — Fresh enough to code on? (per submodule, before its wave runs)
Coming back to an old branch or worktree, never hand out work on what the last `fetch` said: the branch may have been
merged long ago, or the target may have moved under the files the tasks will touch (an agent that codes on a branch hundreds
of commits behind rebuilds work the target already has). Per submodule's branch — `git fetch origin` first (with the
project's remote rewrite if it needs one), then read, don't guess:
- **Position:** `git rev-list --left-right --count origin/<target>...HEAD` (behind / ahead); is the branch already
  merged (`git merge-base --is-ancestor HEAD origin/<target>`, or its PR is `MERGED`)?
- **Overlap:** do the commits the target gained since the merge-base touch the files the tasks list
  (`git diff --name-only <merge-base>..origin/<target>` against the task paths)?
- **Worth reusing for this context?** The branch belongs to the **same ticket** and carries unmerged work still wanted
  (open PR, work in progress) → reuse. Already merged, or abandoned, or the new work is another ticket/context → it carries
  nothing the new work needs: don't build on it as it is.
A submodule whose HEAD is **detached** (typical right after its PR merged) has no branch checked out: read the feature
branch by its name (`probe.sh branch <ticket> <submodule>`) — it exists and is merged → the "merged" row below; it does not
exist → create it from `origin/<target>` as usual.
Decide from those, not from a fixed number of commits:
- Merged, no commit of its own, tree clean → bring it to the target's tip by fast-forward (nothing lost, no force-push); a
  different ticket gets its own new branch (and worktree) from `origin/<target>` instead, never stacked on the old one.
- Own unmerged commits and the target changed files the tasks touch, or it is far behind → **rebase onto
  `origin/<target>` before any coding** (conflicts in the tasks' files are the user's to see; a force-push of an
  already-pushed branch is asked about first, as everywhere).
- Own commits, behind but no overlap, drift small → code on it; the rebase is for PR time.
- Tree dirty → no fast-forward or rebase under uncommitted work: report it. (A re-run the user forced in Step 4 goes on
  from the tree as it is; this check still reports the position.)
Say what was decided and why in one line per submodule (`behind n, overlap: yes → rebased` / `merged → fast-forwarded` /
`reuse as is`), in the report and the state file. Skipping this check is how an agent codes on a stale base.

## Step 5 — Delegate each wave (parallel)
**Transport — pick once, before the first wave.** Resolve `ORCA` the way the `orca-cli` skill's stub says,
then run `ORCA worktree current --json`. It succeeds (the session is inside an Orca-managed worktree)
→ **Orca mode** (below). Anything else — no CLI, Orca not running, not an Orca worktree — → **Agent
mode** (`claude`), except an explicit `--agent kiro`, which stops: "kiro runs only as an Orca terminal." Never `ORCA open` just to get Orca mode.

**Agent mode.** Dispatch every submodule left in the wave **in one message**: one `Agent` call each, `subagent_type`
`general-purpose` (the running agent's own kind), `run_in_background: true`, `model: "sonnet"` and `effort: "medium"` (implementing a brief is routine coding; the coordinator that reviews and accepts the work keeps the session's own model), no
worktree isolation (each agent owns a distinct submodule); the brief tells it to work only inside `PATH`. No waiting
between submodules — this is the whole point. Each agent's final line must be exactly
`✅ implemented <path> (N/M tasks, committed, not pushed)` or `❌ <reason>`.
Per submodule, `PATH` = its path,
`NAME` = its name, and `BRIEF` is composed of (free-form mode: Step 1's `BRIEF` as-is, `NAME` = repo dir name):
- **Grounding:** read the submodule's `CLAUDE.md` + `docs/<service>.md` first; reuse existing
  patterns, don't invent structure.
- **Branch:** create the name `probe.sh branch <ticket> <submodule>` prints (`feat/<ticket>-<slug><suffix>`, config `suffix`; `fix/…` when the ticket's worktree is on a `fix/<ticket>-*` branch — add `--fix`) from the submodule's tracking
  `branch` (config) if missing; else continue on the existing one.
- **Objective + tasks:** only this submodule's checkbox items from `## Tasks`, each with its
  `REQ-NNN`, plus the absolute path of `spec.md`.
- **Allowlist:** only the file paths those tasks name — never write outside it; if a needed file
  isn't listed, **stop** and report the gap (don't widen the allowlist itself).
- **Guard:** work only inside `PATH` and that allowlist; **never run `git push`** — no branch, no flag, no force, not even the feature
  branch: the coordinator pushes after it accepts the work. Never touch a database or docker. (kiro runs with every tool trusted — this is its only brake.)
- **Discipline:** the conventions the submodule's own `CLAUDE.md` states (layering, contract-first, generate steps) and
  its `staging_only` flag from the config — don't restate them from memory.
- **Design (UI tasks):** the spec dir holds a `design-contract.md` and a task touches the FE → the brief carries its path and its `artifact:`.
  Before committing, the worker opens that design (the artifact) beside the page it is coding, same viewport and state, and compares the
  region 1-to-1: every element, label and computed style, not only the contract's tokens. It does not commit a UI that differs; a difference it
  cannot close is named in its final line. `/verify` Part A blocks the same differences (`${CLAUDE_PLUGIN_ROOT}/skills/verify/fidelity.md`, A2–A3).
  That comparison drives a browser: the brief carries the *Browser rules* block of `${CLAUDE_PLUGIN_ROOT}/references/browser-agents.md`, and
  **at most one UI worker drives a browser at a time** (read `uptime` first; two in parallel only when the load is low and the user agrees, with
  the reason in the brief). When a UI worker ends, fails or is stopped, run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-browsers.sh" <its scratch
  directory>`: stopping a worker does not stop the browsers it opened.
- **Verify:** run only the tests of the files you changed (`git diff --name-only <default>...HEAD`, generated files left out): Go → the
  packages that hold them; vitest → `vitest related --run <files>`; pytest → the related tests. The whole suite only if the diff touches
  `go.mod`, `package.json`, a lockfile, `tsconfig*`, a test config or a `Makefile`; no build (e.g. `build:stg`) unless the submodule's
  `CLAUDE.md` requires it. A failure in your diff's scope: stop and report — don't commit red. A failure outside it: run that test on
  `origin/<default>` first; failing there too → say `pre-existing on origin/<default>: <test>` in the final line and carry on
  (`${CLAUDE_PLUGIN_ROOT}/references/scoped-tests.md`).
- **Commit, don't push:** `git add <allowlisted paths>` (never `-A`); one commit citing the task ids; leave the branch unpushed and say so in the final line.

**`AGENT=claude` in Orca mode is a worker like kiro.** The steps of `orca-mode.md` apply to both agents — one path to maintain —
and differ only in the launch (`worker-start --agent claude --model sonnet --effort medium`; no `kiro-cli whoami`) and in the
kiro-only screen pattern for a spent quota. The kiro → claude fallback is that same `worker-start`, and a run mixing both waits on
`check` alone. Agent mode (no Orca) keeps the `Agent` dispatch above.

**Orca mode** — `AGENT=kiro` or `claude`. **REQUIRED:** Read `${CLAUDE_PLUGIN_ROOT}/skills/assign/orca-mode.md` and follow it (it also
says to load the `orca-cli` and `orchestration` skills first). Same `BRIEF`, one worker per submodule, same wave order:
`/assign` is the **coordinator**, Orca creates and supervises each kiro terminal. It covers the `kiro-cli whoami` check, one
Run per invocation, brief-as-a-file, reuse of terminals, `worker-start`, `check --wait` and its message handling, empty waits,
and the kiro → claude fallback. Step 6 below reads what it records.

### Accept, then push (both modes — per submodule, once its worker or agent reports done)
Workers only commit; nothing reaches the remote until the coordinator agrees. For each submodule that reported success:
1. **Read what it did, from git, not from its report:** the branch is the expected `probe.sh branch` name and carries the
   commit(s) (`git -C <PATH> log --oneline origin/<target>..HEAD`), the tree is clean, and `git -C <PATH> diff
   origin/<target>...HEAD --name-only` lists only files inside that submodule's allowlist (or an accepted generated artifact).
   The summary says the tests of the changed files ran green (a `pre-existing on origin/<default>` line is not red), and the diff addresses the tasks' `REQ-NNN`, nothing unrelated.
2. **All hold → accept.** Push the branch: `git -C <PATH> push -u origin <branch>` (`--force-with-lease` only if Step 4b
   rebased it and the user approved that). With `--no-push` stop here instead: report `✅ committed, not pushed` and leave
   the push to the caller. Then check the tasks off (Step 6) and `✅`.
3. **Anything fails → don't push.** Report `❌ not accepted: <what>` with the commits left local, and offer the follow-up
   (a fix task and a re-run on the same worker, like any other retry). A push the hooks refuse (for example the weekend
   PR-branch guard) is reported `✅ committed — push blocked: <reason>`; the user pushes.

## Step 6 — Reconcile + report
Per accepted `✅`, check off its tasks `[x]` in `spec.md` (only the ones it confirmed — never assume
the rest of that submodule's tasks are done because one succeeded). Any `❌` → append to
`.shipkit/assign-failure-<ticket>.md` (submodule, error, recovery) and keep the other submodules'
results — one failure doesn't roll back siblings. Write `.shipkit/assign-<ticket>.md`:
```
# Assign state — <ticket>   run=<run_id>
Wave 1: <submodule-a>          ✅ 3/3 tasks   branch=feat/<TICKET>-<slug>-a   terminal=<handle-1> (kiro) task=<id> dispatch=<id>
        <submodule-b>          ✅ 1/1 tasks   branch=feat/<TICKET>-<slug>-b   terminal=<handle-2> (kiro) task=<id> dispatch=<id>
Wave 2: <submodule-c>          ❌ test failure — see assign-failure-<TICKET>.md  terminal=<handle-3> (kiro, new — a different submodule gets its own) task=<id> dispatch=<id> waits=1
```
(Orca mode only: write the `run`, then each handle, agent kind, submodule, `task` and `dispatch` as soon as its worker is
started or reused — a terminal with no brief yet is `unassigned` — Step 5's reuse check reads them from here.)
Keep earlier runs' lines in that file (a re-run adds or updates its own; the reuse check reads them). Report the same table to the user, then: "Run `/verify --ticket <ticket>` first — it proves each requirement on the running app (FE screenshot, BE data) — then `/pr <ticket>` to open PRs for the completed
submodules." (Failed ones need a fix-and-retry `/assign <ticket> --only <name>` first.)

## Gotchas
- **Parallel within a wave, sequential across waves — never the reverse.** The whole point is not
  waiting on submodule N to start submodule N+1 when nothing actually depends on it; don't collapse
  back to one-at-a-time inside a wave "to be safe."
- **A missing Part order note doesn't mean "ask the user which order."** No note = no known
  dependency = one wave, everything parallel. Only split waves on a note that's actually there.
- **Don't reuse a stale wave plan across retries.** A submodule fixed since the last failure may now
  be `dirty=yes` from that fix — re-probe (Step 2/4) every run, never cache wave membership.
- **Find before you create: reuse the terminal that already has the job, never one that worked on another
  submodule.** A fresh kiro spends minutes loading and knows nothing of the work; a same-job one at its prompt is ready
  now with that context, and a never-briefed one is simply free. Never reuse a terminal that is on a permission prompt
  or of another kind, and never put a second agent on a `PATH` an agent is still working in (reuse = `worker-start
  --terminal`).
- **Starting workers with no `check --wait` pending is an unfinished delivery.** Nothing would process their messages
  or settle them — the user ends up asking whether the agent is done.
- **One Run per invocation.** A second `run-create` from the same terminal fences the first (`consumer_fenced`): reuse
  the id for every wave.
- **kiro liveness is `unverifiable`.** `worker-list` can never prove a kiro agent dead or stuck; absence never
  authorizes stop, abandon, retry or release — only a positive `exited`, or the screen read for `attention` / `login` /
  `shell` / `gone`, does.
- **Trust git, not the agent's last line.** Before checking off tasks, confirm via `probe.sh state` that the feature branch
  exists, carries the worker's commit (`unpushed>0`) and the tree is clean; otherwise record `❌ no commit` / `❌ dirty tree`.
  Only after *Accept, then push* does the branch show `unpushed=0` (with `--no-push` it stays `unpushed>0` on purpose).
- **A worker that pushed anyway is a failure to report**, not a success: say so, and don't `Accept` on top of it.
- **This is not `/pr --implement`.** That flag lives inside `/pr`'s own PR-opening flow and only
  covers submodules not already PR'd. `/assign` runs standalone, any time, independent of PR state,
  and hands off to `/pr` afterward instead of opening PRs itself.
