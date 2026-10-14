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
`AGENT` (default `claude`, the running agent's own CLI; `kiro` runs `kiro-cli chat --tui --trust-all-tools --v3` and needs Orca mode).
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
- **Branch:** create the name `probe.sh branch <ticket> <submodule>` prints (`feat/<ticket>-<slug><suffix>`, config `suffix`) from the submodule's tracking
  `branch` (config) if missing; else continue on the existing one.
- **Objective + tasks:** only this submodule's checkbox items from `## Tasks`, each with its
  `REQ-NNN`, plus the absolute path of `spec.md`.
- **Allowlist:** only the file paths those tasks name — never write outside it; if a needed file
  isn't listed, **stop** and report the gap (don't widen the allowlist itself).
- **Guard:** work only inside `PATH` and that allowlist; never push to `staging` or `main` (the feature
  branch only); never touch a database or docker. (kiro runs with every tool trusted — this is its only brake.)
- **Discipline:** BE → OpenAPI-first (`api/api.yml` → `make gen` → domain → repo → handler); FE →
  BFF proxy + TanStack; Voice → Pipecat, staging-only.
- **Verify:** run the submodule's test command (Makefile `test` target → package-manager test
  script → `pytest`/`go test ./...`, first match). On failure, stop and report — don't push red.
- **Commit + push:** `git add <allowlisted paths>` (never `-A`); one commit; push the branch.

**Orca mode** (REQUIRED: load the `orca-cli` skill first). Same `BRIEF`, one agent per submodule, same
wave order — only the agent's home changes: a visible terminal in the current worktree instead of a hidden
`Agent`. **`--agent kiro`: run `kiro-cli whoami` first**, before creating any terminal — "Not logged in" (or an
error) → create nothing and tell the user (Vietnamese): "kiro chưa đăng nhập — chạy `! kiro-cli login` rồi gọi lại
/assign", then offer the claude fallback (below) for the whole run instead of stopping dead.

**Reuse before create.** One terminal per submodule is for *parallel* work — a wave with several submodules.
A submodule that runs *after* another (a later wave, or one at a time) first tries an idle terminal of the **same
agent kind** (kiro for kiro, claude for claude) that this run already used — its handle and kind are in
`.shipkit/assign-<ticket>.md`; `ORCA terminal list --worktree active --json` must still list it. Reuse it only if
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh" <handle> --timeout-s 30 --poll-s 3 --git <prev PATH> <prev branch>`
returns `STATE=done PUSHED=yes CLEAN=yes` — the agent's own prompt, nothing working, no login/model error or bare
shell, and git (not the agent's last line) confirms its previous task is finished. Anything else (working,
`attention`, `login`, `shell`, `gone`, `PUSHED=no`/`CLEAN=no`, another agent kind, not in the list) → not reusable,
create a new terminal. A reused terminal skips 1 and 2 (no `terminal create`, no `whoami`, no startup wait) and gets
step 3 with its `BRIEF` opening: "Your previous task (<prev NAME>) is finished. From now on work ONLY in `<PATH>`,
on branch `<branch>`, with the allowlist below; do not touch <prev NAME> again." A terminal serves one submodule at
a time and never receives the same brief as another terminal. Then for every submodule in the wave, do 1–3 before
waiting on any of them:
1. `ORCA terminal create --worktree active --title <NAME> --command <AGENT command> --json` → keep the `handle`
   (`claude` → `claude`, `kiro` → `"kiro-cli chat --tui --trust-all-tools --v3"`). The agent shares this checkout and owns only its `PATH`, as in
   Agent mode — never `worktree create` (a second checkout `probe.sh` can't see) or `orchestration task-create`.
2. `ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json`, then `ORCA terminal read
   --terminal <handle> --json` until the agent's own prompt is on screen (kiro: "ask a question or describe a task";
   claude: its prompt box) — `tui-idle` alone is not enough, a bare shell is idle too. Send only then. Not
   satisfied, or a shell prompt / login or model error on screen → `ORCA terminal close --terminal <handle> --json`;
   that submodule is `❌ agent did not start`.
3. `ORCA terminal send --terminal <handle> --text "<BRIEF>" --enter --wait-submit 10 --json`. Never resend on a
   receipt that only says `input_accepted` — it proves nothing about which program got the text: `terminal read`
   and confirm the agent is working (e.g. "Thinking") before counting it started. Text landed in a shell → close
   that terminal, `❌ brief landed in a shell`.
4. **Arm the watcher — part of the send, not a later step.** In the *same message* that confirms the agent is
   working, start per handle with `run_in_background: true`: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh"
   <handle> --git <PATH> <branch>` (`<branch>` = what `probe.sh branch <ticket> <submodule>` printed; `--timeout-s`
   changes the 30-minute default). This holds for **every** brief sent to a terminal: a new one, a reused or
   already-open one, and a later follow-up or fix brief to the same terminal. A parallel wave arms all its
   watchers together, one per handle; if one is already running for that handle, don't start a second. **No brief
   is delivered until its watcher runs**, and a turn never ends after a send with none armed. The script decides
   from the screen, not a final line (the agent may finish in plain prose) and sends one notification per handle.
   When it arrives, act without asking the user: read `STATE` / `PUSHED` / `CLEAN` (the screen tail follows),
   confirm with git — never the agent's last line — then report, start the next wave, or hand the result to review.
   Never answer "is it done?" from memory: read the watcher's output, or run the script once.
   - `done` + `PUSHED=yes` + `CLEAN=yes` → finished; show the screen tail, and take its `✅ implemented <path>
     (N/M tasks)` line as a hint for the task count, not the trigger (no such line → count from the commit and the
     spec's tasks).
   - `done` with `PUSHED=no` or `CLEAN=no` → report "agent finished but not pushed" / "…not clean" (`❌ not
     pushed` / `❌ dirty tree`), never success.
   - Any other `STATE` — `timeout`, `gone`, `login`, `shell`, `attention` (a permission prompt) — is reported to the
     user once, with the terminal handle (`❌ agent did not finish — <state>`). `timeout` relaunches the same
     command **at most twice** (3 × the timeout in all; count them as `relaunches=n` beside the handle in the
     state file); a third `timeout` → `❌ still working after <total> — terminal <handle>`, no further relaunch, and
     the user decides: keep waiting, or the fallback below. Never answer a prompt on their behalf.

**kiro fallback → claude (always asked, never automatic).** A kiro submodule that ends `❌ agent did not start`,
`❌ brief landed in a shell`, `❌ agent did not finish — gone|login|shell`, or hit the relaunch cap (and the
`whoami` failure above) → AskUserQuestion naming the submodule, the state and the terminal handle: "Run `<NAME>`
with claude instead?" (`whoami` failure: the whole run) — `["Switch this submodule to claude", "Leave it ❌",
"Retry kiro"]`. Non-interactive →
leave it `❌`. On a switch: close the failed kiro terminal (`ORCA terminal close`, unless the user wants to read
it), create a **claude** terminal for that submodule (steps 1–4 with `AGENT=claude`; no `whoami`), and open its
`BRIEF` with: "A previous agent may have left partial work on `<branch>` — run `git status` / `git log` first and
continue from it; don't redo or discard it." Mark it `kiro → claude` in the state file; the other submodules stay
on kiro. `attention`, `PUSHED=no` and `CLEAN=no` are not offered a switch: the agent did run, so those go to the
user as they are.
Leave terminals open so the user can read them; record the handles in the state file. Checkpoint with
`ORCA worktree set --worktree active --comment "assign <ticket>: wave N running (<names>)" --json`.
Step 3's "confirm the agent is working" rule applies to a reused terminal too.

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
Wave 1: ai-roleplay-be        ✅ 3/3 tasks   branch=feat/AR-450-rooms-be     terminal=term_a1 (kiro)
        ai-roleplay-voice     ✅ 1/1 tasks   branch=feat/AR-450-rooms-voice  terminal=term_b2 (kiro)
Wave 2: ai-roleplay           ❌ test failure — see assign-failure-AR-450.md  terminal=term_a1 (kiro, reused from wave 1)
```
(Orca mode only: write each handle and agent kind as soon as its terminal is created or reused — Step 5's reuse
check reads them from here.)
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
- **Reuse an idle same-kind terminal for sequential waves; spawn only for parallel work or when nothing idle
  exists.** A fresh kiro spends minutes loading before it accepts input and knows nothing of the earlier wave's
  output; a finished one at its prompt is ready now and has that context. Never reuse a terminal that is working,
  on a permission prompt, or of another kind.
- **Sending a brief without arming `wait-for-agent.sh` is an unfinished delivery.** No watcher, no notification —
  the user ends up asking whether the agent is done.
- **Trust git, not the agent's last line.** Before checking off tasks, confirm via `probe.sh state` that
  the feature branch exists and is pushed (`unpushed=0`); otherwise record `❌ not pushed`.
- **This is not `/pr --implement`.** That flag lives inside `/pr`'s own PR-opening flow and only
  covers submodules not already PR'd. `/assign` runs standalone, any time, independent of PR state,
  and hands off to `/pr` afterward instead of opening PRs itself.
