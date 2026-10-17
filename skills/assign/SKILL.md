---
name: assign
description: "Use when a ticket's spec.md tags tasks across ≥2 submodules and they'd otherwise get implemented one submodule at a time — hands each submodule's allowlisted tasks to a parallel background agent (kiro terminals by default, claude as fallback) so they implement concurrently, in dependency waves per the plan's Part order. Also delegates a single target or a free-form task (single-repo, no config, non-ticket args) to one agent. Trigger: /assign <jira-ticket | task>. Examples: \"/assign AR-450\", \"parallelize AR-458's implementation across submodules\", \"stop doing these submodules one at a time\""
argument-hint: "<jira-ticket | task text> [--only <submodule,...>] [--agent claude|kiro]"
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
2. One commit + push per submodule's feature branch (creates the branch if missing).
3. `specs/NNN-slug/spec.md` — check off `[x]` tasks the agent confirmed done (and git verifies).
4. `.shipkit/assign-<ticket>.md` — per-submodule wave/status log (Orca mode: plus each agent's terminal handle).
5. `.shipkit/assign-failure-<ticket>.md` — on any agent failure (submodule, error, recovery).
6. Orca mode, `AGENT=kiro` only: one `orchestration run-create` per invocation, then `worker-start`, `check`, `reply`, `worker-retain` / `worker-release` / `worker-stop` / `worker-abandon` (the last two only on positive proof the agent exited) — never an Orca worktree, `dispatch --inject`, `orchestration reset`, a brief sent with `terminal send`, or a **claude** terminal (see Step 5).
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
`AGENT` (default `kiro` in Orca mode, `claude` in Agent mode — Step 5 picks the mode; an explicit flag always wins; `claude` is always spawned as background `Agent` calls from the running claude session, never as a terminal. `kiro` runs as an Orca-supervised worker (its tools are trusted, so the BRIEF's Guard is its only brake) and needs Orca mode).
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
  Wave 1 (parallel): <submodule-a>, <submodule-b>
  Wave 2 (parallel): <submodule-c>
  ```

## Step 4 — Ground-truth skip check (per submodule, before its wave runs)
From the Step 2 probe: `dirty=yes` or `unpushed>0` on that submodule's `feat/<ticket>-*` branch means
work already started. Default: skip it (report "already in progress — skip", don't overwrite).
To force a re-run anyway, the user must say so explicitly — AskUserQuestion: "`<submodule>` already
has {dirty|unpushed} changes on its branch — re-run its agent anyway and let it continue from
there, or skip?" (`--only <name>` alone does not imply force.)

## Step 4b — Fresh enough to code on? (per submodule, before its wave runs)
Coming back to an old branch or worktree, never hand out work on what the last `fetch` said: the branch may have been
merged long ago, or the target may have moved under the files the tasks will touch (a returning worktree once had its
agent coding on a branch hundreds of commits behind). Per submodule's branch — `git fetch origin` first (with the
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

**`AGENT=claude` never gets a terminal — not even in Orca mode.** `/assign` itself runs inside a claude session (in Orca
mode that is the coordinator's terminal), so the claude agents are that session's own background `Agent` calls — dispatch
them exactly as **Agent mode** above (one message, `run_in_background: true`), whether `AGENT=claude` came from the flag
or from the kiro fallback. Never `terminal create` another claude terminal to run a submodule: a second claude session
adds nothing the coordinator can't spawn, and leaves a stray terminal. The worker steps below are for kiro only; a
run mixing both (kiro workers plus fallback claude `Agent` calls) waits on `check` and the `Agent`
notifications together.

**Orca mode** (REQUIRED: load the `orca-cli` and `orchestration` skills first; `ORCA skills get orchestration` is the
version-matched guide). Same `BRIEF`, one worker per submodule, same wave order — only the agent's home and the plumbing
change: `/assign` is the **coordinator**; Orca creates and supervises each kiro terminal itself and injects the brief.
**`AGENT=kiro` (the default, or the flag): run `kiro-cli whoami` first**, before starting a worker on a new terminal (a run that only reuses live kiro terminals skips it) — "Not logged in" (or an
error) → start nothing and tell the user (Vietnamese): "kiro chưa đăng nhập — chạy `! kiro-cli login` rồi gọi lại
/assign", then offer the claude fallback (below) for the whole run instead of stopping dead. (Orchestration does not check
the login, and what a worker would show on a login screen was not verified — hence the check up front.)

**One Run per invocation.** Exactly one `ORCA orchestration run-create --objective "assign <ticket>" --json`, its id reused
for every wave and every `--run`, written to the state file (`run=<run_id>`). A second `run-create` from the same terminal
**fences** the first (`worker-start --run <old>` → `consumer_fenced`). A later `/assign` of the same ticket is a new
invocation → a new Run; terminals an older Run retained are still reusable (`--terminal`, below).

**The brief goes in as a file.** Compose `BRIEF` into a file in the session scratchpad and pass `--spec "$(cat <file>)"` —
never inline: multi-line text with backticks, `$` and Vietnamese then arrives byte for byte. The `BRIEF` components above
already cover the guide's task-spec contract (Target/Change = Branch + Objective + tasks, Constraints/Ownership =
Allowlist + Guard + Discipline, Observable acceptance = Verify). Orca-mode differences, added to the `BRIEF`:
- **Finish with `worker_done`, not a final line:** `--outcome succeeded` or `--outcome failed` (failure is never only
  prose); the three-sentence summary names `implemented <path> (N/M tasks)`. An allowlist gap → stop, `worker_done
  --outcome failed` naming the gap; never widen the allowlist. (Agent mode keeps the `✅` / `❌` final line.)
- **It may `ask`** (the command in its preamble). The coordinator answers **only** from `spec.md`, the plan or the
  submodule's `CLAUDE.md`; a product decision, or anything that widens the allowlist → `AskUserQuestion` or a refusing
  reply. A permission prompt on a terminal is never answered on the user's behalf.

**Reuse before create — find first, start last.** Before starting a worker on a new terminal, look for one that already
belongs to this job, in this order (`ORCA terminal list --worktree active --json` is the ground truth; the handle, the
agent kind and the submodule each terminal serves are in `.shipkit/assign-<ticket>.md`, which also survives an earlier
`/assign` run of the same ticket):
1. **Same job:** a terminal already serving this submodule (same `PATH` and branch — a follow-up task, a later wave, a
   fix after `/verify`, a retry). It has the context; reuse it.
2. **Never briefed:** a terminal recorded `unassigned` (a start that did not reach a brief). It holds no work, so any
   submodule may take it.

A terminal that has worked on one submodule is **never** handed another — a different submodule always gets its own.
Kiro terminals only (claude has none). A candidate is reusable iff `bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh"
<handle> --once` reads `SCREEN=agent` (idle, an input box up). `working` → **do not start a second agent on the same
`PATH`**: its own `worker_done` has to settle first (wait on it below), then reuse. `attention`, `login`, `shell`, `gone`,
another kind, or not in the list → not reusable; a dead one is released only on positive proof of exit (`worker-list` /
`worker-show` say `exited`), never from absence. Reuse = `worker-start --terminal <handle>` (no `whoami`, no new
terminal), its `BRIEF` opening for same-job reuse: "New task on the same submodule (`<PATH>`, branch `<branch>`) — the
allowlist below replaces the previous one." A terminal serves one submodule and never receives another's brief.

**Start the whole wave before waiting.** For every submodule in the wave:
1. `ORCA orchestration worker-start --spec "$(cat <brief file>)" --agent kiro --worktree current --run <RUN> --json`
   (add `--terminal <handle>` for a reuse). A wave starts its workers in parallel (`&` then `wait` in one `bash -c`). The
   agent shares this checkout and owns only its `PATH`, as in Agent mode. Always `--worktree current` — never `worktree
   create` (a second checkout `probe.sh` can't see) — and never `--agent claude`, `dispatch --inject`, or a brief sent with
   `terminal send`. A brief can't land in a shell: Orca launches the agent itself.
2. Read the receipt: `taskId`, `dispatchId`, `state: ready`, `stage: input_accepted`, `turnStart: unsupported`. The
   terminal handle is `worker-show --dispatch <id>` → `worker.agentTerminalHandle`. **`input_accepted` is not proof the
   agent took the brief** (Orca cannot observe kiro's turn), so make **one** read-only confirmation: the worker's first
   message in `check`, or `wait-for-agent.sh <handle> --once` → `SCREEN=working` (read a few times, 5 s apart). `shell` /
   `login` / `gone` → `❌ agent did not start`; anything else is a checkpoint, never a resend.
3. `worker-start` **non-zero** (or `ok: false`) → `❌ agent did not start` with the receipt's `error.code` /
   `failedStage` / `residualResources`. A refusal before any launch (e.g. `agent_unconfigured`) leaves nothing behind. A
   start that launched leaves a terminal owned by that worker (`worker-list` shows it `reclaimable`): release it with
   `worker-release` (or, if the user wants to read it, `worker-retain` and record it `unassigned`) — never `terminal close` — and retry only with `--task <id> --retry-of <dispatch>`, never a blind
   relaunch. (A failure after launch was not reproduced; this follows the recovery reference.)
4. Record per submodule in the state file: `task=<id> dispatch=<id>` beside the handle, kind and submodule.

**Wait, process everything, settle before the ack.** A turn never ends after starting workers with no `check --wait`
pending. Wait with `ORCA orchestration check --run <RUN> --wait --types worker_done,escalation,question --timeout-ms
1800000 --json` via Bash `run_in_background: true` (the output file is written and a notification arrives when it ends),
so a mixed run waits on `check` and the claude `Agent` notifications together. The output can hold more than one JSON
document: parse every one (a `raw_decode` loop) and use the one that carries `result.deliveryId` / `messages`. A consuming
`check` **replays** its delivery until `check --ack <delivery_id>`. Process every message, then ack — and settle each
worker *before* acking:
- **`question`** → answer per the rule above with `ORCA orchestration reply --id <msg_id> --body "…"`; it unblocks the
  worker.
- **`worker_done`** (`from_handle` = the terminal; payload `outcome`; `subject` / `body` = the worker's summary) →
  `outcome=failed` → `❌` + the summary. `outcome=succeeded` → **trust git, not the report**: `probe.sh state <ticket>`
  (branch exists, `unpushed=0`, clean), or the same three facts — HEAD branch == `<branch>`, local HEAD == `git ls-remote
  --heads origin <branch>`, clean tree. Pushed and clean → `✅` (task count from the summary as a hint, then from the
  commit and the spec's tasks); not pushed → `❌ not pushed`; dirty → `❌ dirty tree`. **Either outcome**, then the
  terminal's next owner, exactly one: **reuse** it for the next brief, **`worker-retain --dispatch <id>`** (the default — the user reads the
  terminals and the next wave or fix reuses them), or `worker-release` (only if the user asks). A settled kiro terminal
  left undecided stays `reclaimable`.
- **`escalation`** → show it to the user once, answer nothing for them. (This message type was not reproduced.)
- Then `ORCA orchestration check --run <RUN> --ack <delivery_id> --wait --types worker_done,escalation,question
  --timeout-ms 1800000 --json` acks and waits for the next one in one call.
Wait for the **whole wave** to settle before starting the next — a later wave may depend on what an earlier one just
pushed (e.g. FE reading BE's freshly generated types). Before the turn ends, `ORCA orchestration worker-list --run <RUN>
--terminal-state reclaimable --json` must be empty.

**An empty wait is a checkpoint, not a failure.** After three consecutive empty waits (90 minutes), enumerate:
`worker-list --run <RUN>` and `wait-for-agent.sh <handle> --once` per worker. kiro's liveness is always `unverifiable`
(`missing_status`) — the screen read is the only signal, and absence never authorizes stopping, abandoning, retrying or
releasing. `attention` (a permission prompt), `login`, `shell`, `gone` → report once with the handle (`❌ agent did not
finish — <state>`), never answer a prompt; `working` → `❌ still working after 90 min — terminal <handle>`, and the user
decides: keep waiting, or the fallback below. Count the waits as `waits=n` beside the handle in the state file. There is no
relaunch: `worker-stop` / `worker-abandon` only on positive proof the agent exited (an `exited` verdict, or a transcript
whose last turn sent no `worker_done`).

**kiro fallback → claude (always asked, never automatic).** A kiro submodule that ends `❌ agent did not start`,
`❌ agent did not finish — gone|login|shell`, or hit the 90-minute wait (and the `whoami` failure above) →
AskUserQuestion naming the submodule, the state and the terminal handle: "Run `<NAME>` with claude instead?" (`whoami`
failure: the whole run) — `["Switch this submodule to claude", "Leave it ❌", "Retry kiro"]`. Non-interactive → leave it
`❌`. On a switch: release the failed kiro worker (`worker-release` — reclaimable after a failed start — or `worker-stop`
on proven exit; never `terminal close`; `worker-retain` instead if the user wants to read it), spawn a background
**claude `Agent`** for that submodule (Agent-mode dispatch from this session — **no** claude terminal; no `whoami`), and
open its `BRIEF` with: "A previous agent may have left partial work on `<branch>` — run `git status` / `git log` first and
continue from it; don't redo or discard it." Mark it `kiro → claude` in the state file; the other submodules stay on
kiro. `attention`, `❌ not pushed` and `❌ dirty tree` are not offered a switch: the agent did run, so those go to the user as
they are.
Leave terminals open so the user can read them (`worker-retain`); record the handles in the state file. Checkpoint with
`ORCA worktree set --worktree active --comment "assign <ticket>: wave N running (<names>)" --json`.

## Step 6 — Reconcile + report
Per agent's `✅`, check off its tasks `[x]` in `spec.md` (only the ones it confirmed — never assume
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
- **Trust git, not the agent's last line.** Before checking off tasks, confirm via `probe.sh state` that
  the feature branch exists and is pushed (`unpushed=0`); otherwise record `❌ not pushed`.
- **This is not `/pr --implement`.** That flag lives inside `/pr`'s own PR-opening flow and only
  covers submodules not already PR'd. `/assign` runs standalone, any time, independent of PR state,
  and hands off to `/pr` afterward instead of opening PRs itself.
