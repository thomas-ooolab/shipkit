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
6. Orca mode, `AGENT=kiro` only: one Orca terminal per submodule (`terminal create` / `send`) — never an Orca worktree or orchestration task, and never a new **claude** terminal (see Step 5).
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
`AGENT` (default `kiro` in Orca mode, `claude` in Agent mode — Step 5 picks the mode; an explicit flag always wins; `claude` is always spawned as background `Agent` calls from the running claude session, never as a terminal. `kiro` runs `kiro-cli chat --tui --trust-all-tools --v3` and needs Orca mode).
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
mode that is the planner's terminal), so the claude agents are that session's own background `Agent` calls — dispatch
them exactly as **Agent mode** above (one message, `run_in_background: true`), whether `AGENT=claude` came from the flag
or from the kiro fallback. Never `terminal create` another claude terminal to run a submodule: a second claude session
adds nothing the planner can't spawn, and leaves a stray terminal. The terminal steps below are for kiro only; a
run mixing both (kiro terminals plus fallback claude `Agent` calls) arms the kiro watchers and waits for the `Agent`
notifications together.

**Orca mode** (REQUIRED: load the `orca-cli` skill first). Same `BRIEF`, one agent per submodule, same
wave order — only the agent's home changes: a visible terminal in the current worktree instead of a hidden
`Agent`. **`AGENT=kiro` (the default, or the flag): run `kiro-cli whoami` first**, before creating any terminal — "Not logged in" (or an
error) → create nothing and tell the user (Vietnamese): "kiro chưa đăng nhập — chạy `! kiro-cli login` rồi gọi lại
/assign", then offer the claude fallback (below) for the whole run instead of stopping dead.

**Reuse before create — find first, `terminal create` last.** Before opening any terminal, look for one that already
belongs to this job, in this order (`ORCA terminal list --worktree active --json` is the ground truth; the handle, the
agent kind and the submodule each terminal serves are in `.shipkit/assign-<ticket>.md`, which also survives an earlier
`/assign` run of the same ticket — a terminal from that run counts, not only one from this run):
1. **Same job:** a terminal already serving this submodule (same `PATH` and branch — a follow-up task, a later wave, a
   fix after `/verify`, a retry). It has the context; reuse it.
2. **Never briefed:** a terminal opened by this ticket's run that received no brief yet (state file: `unassigned` —
   a start that was slow or interrupted). It holds no work, so any submodule may take it.

A terminal that has worked on one submodule is **never** handed another — a BE terminal does not become the FE one, and
a different submodule always gets its own (that is the only reason to open a new one besides "nothing found").
Kiro terminals only (claude has none). A candidate is reused iff
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh" <handle> --timeout-s 30 --poll-s 3 --git <PATH> <branch>`
returns `STATE=done` (the agent's own prompt, nothing working, no login/model error or bare shell; `PUSHED`/`CLEAN`
need not be `yes` — it is the same agent continuing its own work); an `unassigned` one only needs `--once` →
`SCREEN=agent`. `STATE=timeout` (still working) on a same-job terminal → **do not open a second agent on the same
`PATH`**: arm the watcher on it (step 4) and send the new brief when it is done. `attention`, `login`, `shell`, `gone`,
another kind, or not in the list → not reusable: close it if dead (`shell`/`login`/`gone`), then create a new one. A
reused terminal skips 1 and 2 (no `terminal create`, no `whoami`, no startup wait) and gets step 3, its `BRIEF` opening
for same-job reuse: "New task on the same submodule (`<PATH>`, branch `<branch>`) — the allowlist below replaces the
previous one." A terminal serves one submodule and never receives the same brief as another terminal. A terminal that
fails the ready check as `unknown` is **kept open** and recorded `unassigned` — the next try reuses it instead of
opening another. Then for every submodule in the wave, do 1–3 before waiting on any of them:
1. `ORCA terminal create --worktree active --title <NAME> --command <AGENT command> --json` → keep the `handle`
   (`claude` → `claude`, `kiro` → `"kiro-cli chat --tui --trust-all-tools --v3"`). The agent shares this checkout and owns only its `PATH`, as in
   Agent mode — never `worktree create` (a second checkout `probe.sh` can't see) or `orchestration task-create`.
2. **Ready = behaviour, not a banner string** (kiro's v3 TUI never prints "ask a question or describe a task").
   `ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json` (not satisfied: don't conclude,
   carry on to the read), then `bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh" <handle> --once` → `SCREEN=` and
   `HASH=` (keep the HASH as *before*). Read-only; it sends nothing.
   - `agent` (an input box is up, nothing working) → go to 3. Background status lines — "What's new", "Fetching your
     cloud config", a model/credits load — are not a reason to wait: the agent already takes input.
   - `shell` / `login` / `gone` on two reads 3 s apart → `ORCA terminal close --terminal <handle> --json`, send
     nothing, `❌ agent did not start`. **A brief is never sent while the screen reads `shell`:** in a shell it would
     run as commands. That is why the check is "no shell/login/error", decided on the screen's structure (input box
     vs. a prompt line), before the send, and the *proof* the agent took the brief comes after it.
   - `unknown` (TUI still drawing, unfamiliar screen) → read again every 3 s, up to 10 times; still `unknown` →
     `❌ agent did not start` with the screen tail shown to the user, terminal left open and recorded `unassigned` (a
     retry reuses it); never send blind. `attention` → `❌`, show it,
     answer nothing.
3. `ORCA terminal send --terminal <handle> --text "<BRIEF>" --enter --wait-submit 10 --json`. `input_accepted` proves
   nothing about which program got the text, so confirm by what the screen *does*: `wait-for-agent.sh <handle> --once`
   up to 5 times, 5 s apart. Started = `SCREEN=working`, **or** `HASH` differs from the one before the send while the
   screen is not `shell`/`login` (the brief is now in the transcript; a brief only typed into the input box leaves
   `HASH` unchanged). `shell` → close the terminal, `❌ brief landed in a shell`; `login` → `❌ agent did not start`.
   No change and not working after 5 reads → press Enter once (`terminal send --text "" --enter`: it submits a brief
   left unsubmitted in the input box and does nothing on an empty one — never resend the brief) and read 3 more times;
   still nothing → `❌ brief not received`, show the screen tail. Never resend the brief itself.
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
it), spawn a background **claude `Agent`** for that submodule (Agent-mode dispatch from this session — **no** claude terminal; no
`whoami`), and open its `BRIEF` with: "A previous agent may have left partial work on `<branch>` — run `git status` / `git log` first and
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
Wave 1: <submodule-a>          ✅ 3/3 tasks   branch=feat/<TICKET>-<slug>-a   terminal=<handle-1> (kiro)
        <submodule-b>          ✅ 1/1 tasks   branch=feat/<TICKET>-<slug>-b   terminal=<handle-2> (kiro)
Wave 2: <submodule-c>          ❌ test failure — see assign-failure-<TICKET>.md  terminal=<handle-3> (kiro, new — a different submodule gets its own)
```
(Orca mode only: write each handle, agent kind and submodule as soon as its terminal is created or reused — `unassigned`
until its brief is sent — Step 5's reuse check reads them from here.)
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
- **Find before you create: reuse the terminal that already has the job, never one that worked on another
  submodule.** A fresh kiro spends minutes loading and knows nothing of the work; a same-job one at its prompt is ready
  now with that context, and a never-briefed one is simply free. Never reuse a terminal that is on a permission prompt
  or of another kind, and never put a second agent on a `PATH` an agent is still working in.
- **Sending a brief without arming `wait-for-agent.sh` is an unfinished delivery.** No watcher, no notification —
  the user ends up asking whether the agent is done.
- **Trust git, not the agent's last line.** Before checking off tasks, confirm via `probe.sh state` that
  the feature branch exists and is pushed (`unpushed=0`); otherwise record `❌ not pushed`.
- **This is not `/pr --implement`.** That flag lives inside `/pr`'s own PR-opening flow and only
  covers submodules not already PR'd. `/assign` runs standalone, any time, independent of PR state,
  and hands off to `/pr` afterward instead of opening PRs itself.
