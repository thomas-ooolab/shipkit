# /assign — Step 5, Orca mode (kiro and claude workers under Orca orchestration)

> Loaded by `/assign` in Orca mode, `AGENT=kiro` or `claude`. `BRIEF` and the wave plan are the ones SKILL.md built in Steps 1–5.

**Orca mode** (REQUIRED: load the `orca-cli` and `orchestration` skills first; `ORCA skills get orchestration` is the
version-matched guide). Same `BRIEF`, one worker per submodule, same wave order — only the agent's home and the plumbing
change: `/assign` is the **coordinator**; Orca creates and supervises each worker terminal (kiro or claude) itself and injects the brief.
**`AGENT=kiro` (the default, or the flag): run `kiro-cli whoami` first**, before starting a worker on a new terminal (a run that only reuses live terminals skips it) — "Not logged in" (or an
error) → start nothing and tell the user (in their language): "kiro is not logged in — run `! kiro-cli login`, then call
/assign", then offer the claude fallback (below) for the whole run instead of stopping dead. (Orchestration does not check
the login, and what a worker would show on a login screen was not verified — hence the check up front.)

**One Run per invocation.** Exactly one `ORCA orchestration run-create --objective "assign <ticket>" --json`, its id reused
for every wave and every `--run`, written to the state file (`run=<run_id>`). A second `run-create` from the same terminal
**fences** the first (`worker-start --run <old>` → `consumer_fenced`). A later `/assign` of the same ticket is a new
invocation → a new Run; terminals an older Run retained are still reusable (`--terminal`, below).

**The brief goes in as a file.** Compose `BRIEF` into a file in the session scratchpad and pass `--spec "$(cat <file>)"` —
never inline: multi-line text with backticks, `$` and non-ASCII text then arrives byte for byte. The `BRIEF` components above
already cover the guide's task-spec contract (Target/Change = Branch + Objective + tasks, Constraints/Ownership =
Allowlist + Guard + Discipline, Observable acceptance = Verify). Orca-mode differences, added to the `BRIEF`:
- **Finish with `worker_done`, not a final line:** `--outcome succeeded` or `--outcome failed` (failure is never only
  prose); the three-sentence summary names `implemented <path> (N/M tasks)`. An allowlist gap → stop, `worker_done
  --outcome failed` naming the gap; never widen the allowlist. (Agent mode keeps the `✅` / `❌` final line.)
- **It may `ask`** (the command in its preamble). The coordinator answers **only** from `spec.md`, the plan or the
  submodule's `CLAUDE.md`; a product decision, or anything that widens the allowlist → `AskUserQuestion` or a refusing
  reply. A permission prompt on a terminal is never answered on the user's behalf.
- **UI task:** the `Design` bullet of the `BRIEF` applies; the `worker_done` summary says the 1-to-1 comparison was done, or names the
  differences left. Once that worker settles, or is stopped, run `scripts/cleanup-browsers.sh` on its scratch directory (SKILL.md, *Design*).

**Reuse before create — find first, start last.** Before starting a worker on a new terminal, look for one that already
belongs to this job, in this order (`ORCA terminal list --worktree active --json` is the ground truth; the handle, the
agent kind and the submodule each terminal serves are in `.shipkit/assign-<ticket>.md`, which also survives an earlier
`/assign` run of the same ticket):
1. **Same job:** a terminal already serving this submodule (same `PATH` and branch — a follow-up task, a later wave, a
   fix after `/verify`, a retry). It has the context; reuse it.
2. **Never briefed:** a terminal recorded `unassigned` (a start that did not reach a brief). It holds no work, so any
   submodule may take it.

A terminal that has worked on one submodule is **never** handed another — a different submodule always gets its own.
**Reuse is tried for every agent kind — kiro, claude, codex, … — and the terminal's own agent keeps running; a reuse never changes it** (to
get a different agent, start a new terminal). Orca decides whether it accepts the call (below). What makes a candidate reusable depends on its kind:
- **kiro:** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh" <handle> --once` reads `SCREEN=agent` (idle, an input box up).
- **any other agent:** `ORCA orchestration worker-list --run <RUN> --json` (or `worker-show --dispatch <id>`) still lists the terminal as
  an Orca-managed agent whose last `worker_done` has settled — not `exited`, and not `retained` for a reason you did not set.

`working` → **do not start a second agent on the same `PATH`**: its own `worker_done` has to settle first (wait on it below), then
reuse. `attention`, `login`, `shell`, `gone`, or not in the list → not reusable; a dead one is released only on positive proof of
exit (`worker-list` / `worker-show` say `exited`), never from absence.

**The reuse call** carries only `--spec`, `--worktree current` and `--run`, plus `--terminal`:
`ORCA orchestration worker-start --terminal <handle> --spec "$(cat <brief file>)" --worktree current --run <RUN> --json`
(no `whoami`, no new terminal). **Never add `--agent`, `--model` or `--effort`** — Orca refuses each: "`--terminal` reuses an existing
agent and cannot combine with `--agent`", "`--model` and `--effort` cannot be applied when reusing an existing terminal". The `BRIEF`
opens, for same-job reuse: "New task on the same submodule (`<PATH>`, branch `<branch>`) — the allowlist below replaces the previous
one." A terminal serves one submodule and never receives another's brief.

**Try the reuse first; if Orca refuses it, start a new worker — once.** Tested on a real Orca (2026-10-23, two claude workers, each
`worker_done` / `succeeded`, `SCREEN=agent`, `terminalState=reclaimable`, `terminal list` showing `agentIdentity: claude`): the
documented call was refused **every time** with `agent_unconfigured` — "Terminal <handle> is not running a recognized agent" — right after
`worker_done`, after the ack, after a screen read and after minutes idle. The same session showed that `--terminal` with `--agent`,
`--model` or `--effort` is refused with the messages above, so a refusal for flags is yours to fix and one for `agent_unconfigured` is
not. Never confirmed to work for any agent kind; do not count on it. Separately, one of the two terminals later read `release=retained`,
`retainedReason=user_takeover`, `ownership=user_owned` (the other never did): no `worker-start`, `check --ack`, `terminal read` or `terminal show`
call produced that, so a person touching the terminal in Orca is the likely cause (not proven), and `worker-release` on such a terminal
answers ok yet leaves it retained. So: on any refusal, start a new worker for that submodule (the normal `worker-start`, with its own `--agent`),
write `reuse refused: <Orca's message verbatim>` on that submodule's line of `.shipkit/assign-<ticket>.md`, and do not retry the reuse in
this run.

**Start the whole wave before waiting.** For every submodule in the wave:
1. `ORCA orchestration worker-start --spec "$(cat <brief file>)" --agent <AGENT> --worktree current --run <RUN> --json`
   (a reuse is the call under *Reuse before create*: `--terminal <handle>` with only `--spec`, `--worktree current` and `--run` — no `--agent`, `--model` or `--effort`). A wave starts its workers in parallel (`&` then `wait` in one `bash -c`). The
   agent shares this checkout and owns only its `PATH`, as in Agent mode. Always `--worktree current` — never `worktree
   create` (a second checkout `probe.sh` can't see) — and never `dispatch --inject` or a brief sent with
   `terminal send`. A brief can't land in a shell: Orca launches the agent itself. `claude` always gets `--model sonnet --effort medium`
   (implementing a brief is routine coding); kiro gets neither flag — it runs with the model of its own config (the CLI takes them only for Claude,
   Codex, Cursor, Antigravity and Muse).
2. Read the receipt: `taskId`, `dispatchId`, `state: ready`, `stage: input_accepted`, `turnStart` (`unsupported` for kiro, `observed` for claude). The
   terminal handle is `worker-show --dispatch <id>` → `worker.agentTerminalHandle`. **`input_accepted` is not proof the
   agent took the brief** (Orca cannot observe kiro's turn; for claude `turnStart: observed` already is the confirmation), so for kiro make **one** read-only confirmation: the worker's first
   message in `check`, or `wait-for-agent.sh <handle> --once` → `SCREEN=working` (read a few times, 5 s apart). `shell` /
   `login` / `limit` / `gone` → `❌ agent did not start`; anything else is a checkpoint, never a resend.
3. `worker-start` **non-zero** (or `ok: false`) → `❌ agent did not start` with the receipt's `error.code` /
   `failedStage` / `residualResources`. A refusal before any launch (e.g. `agent_unconfigured`) leaves nothing behind. A
   start that launched leaves a terminal owned by that worker (`worker-list` shows it `reclaimable`): release it with
   `worker-release` (or, if the user wants to read it, `worker-retain` and record it `unassigned`) — never `terminal close` — and retry only with `--task <id> --retry-of <dispatch>`, never a blind
   relaunch. (A failure after launch was not reproduced; this follows the recovery reference.)
4. Record per submodule in the state file: `task=<id> dispatch=<id>` beside the handle, kind and submodule.

**Wait, process everything, settle before the ack.** A turn never ends after starting workers with no `check --wait`
pending. Wait with `ORCA orchestration check --run <RUN> --wait --types worker_done,escalation,question --timeout-ms
600000 --json` via Bash `run_in_background: true` (the output file is written and a notification arrives when it ends),
so every worker, kiro or claude, is waited on the same way. The output can hold more than one JSON
document: parse every one (a `raw_decode` loop) and use the one that carries `result.deliveryId` / `messages`. A consuming
`check` **replays** its delivery until `check --ack <delivery_id>`. Process every message, then ack — and settle each
worker *before* acking:
- **`question`** → answer per the rule above with `ORCA orchestration reply --id <msg_id> --body "…"`; it unblocks the
  worker.
- **`worker_done`** (`from_handle` = the terminal; payload `outcome`; `subject` / `body` = the worker's summary) →
  `outcome=failed` → `❌` + the summary. `outcome=succeeded` → **trust git, not the report**: `probe.sh state <ticket>`
  (branch exists, `unpushed>0` — the worker committed and, by the brief, did not push — tree clean). Then run SKILL.md's
  *Accept, then push*: accepted → the coordinator pushes (not with `--no-push`) → `✅` (task count from the summary as a
  hint, then from the commit and the spec's tasks); no commit → `❌ no commit`; dirty → `❌ dirty tree`; a worker that pushed
  anyway (`unpushed=0` before you pushed) → `❌ worker pushed` — report it, don't accept on top. **Either outcome**, then the
  terminal's next owner, exactly one: **reuse** it for the next brief; a `❌` or not-accepted worker → **`worker-retain --dispatch <id>`** (the
  user reads what went wrong); a `✅` worker → left as it is and **closed on its own after 3 idle minutes** with no further request (*Idle close*
  below, which starts only in Step 6, after the last wave), or `worker-release` at once if the user asks. **Release a `✅` terminal only when
  no task of the same submodule is left** (a later wave, a retry, a fix after `/verify`): a released terminal may no longer be reusable. A settled terminal left undecided stays `reclaimable`.
- **`escalation`** → show it to the user once, answer nothing for them. (This message type was not reproduced.)
- Then `ORCA orchestration check --run <RUN> --ack <delivery_id> --wait --types worker_done,escalation,question
  --timeout-ms 600000 --json` acks and waits for the next one in one call.
Wait for the **whole wave** to settle before starting the next — a later wave may depend on what an earlier one just
accepted (e.g. FE reading BE's freshly generated types). Before the turn ends, `ORCA orchestration worker-list --run <RUN>
--terminal-state reclaimable --json` must be empty, except the `✅` terminals whose idle close is pending.

**Every empty wait (10 minutes) is a screen look.** `check --wait` returns nothing while kiro is stuck or out of quota, so each empty wait
runs `wait-for-agent.sh <handle> --once` for every worker not yet settled (read-only: nothing is sent, nothing is killed).
- `SCREEN=limit` (kiro's out-of-quota notice; the pattern is `LIMIT` in that script) → **stop waiting for that worker now**:
  `❌ agent hit its usage limit — terminal <handle>`, then audit its submodule before anything else (`git -C <PATH> log --oneline
  origin/<target>..HEAD`, `git -C <PATH> status --short`: which commits exist, whether the tree is dirty), then the fallback below. The
  other workers keep running; a wave still settles as a whole.
- `SCREEN=agent` (an idle input box) on two consecutive looks, for a worker that took its brief and sent no `worker_done` →
  `❌ agent idle without worker_done — terminal <handle>`: it stopped without reporting. Audit git the same way, then the fallback below.
- Any other state is only counted (`waits=n`, below).

**An empty wait is a checkpoint, not a failure.** After nine consecutive empty waits (90 minutes), enumerate:
`worker-list --run <RUN>` and `wait-for-agent.sh <handle> --once` per worker. kiro's liveness is always `unverifiable`
(`missing_status`) — the screen read is the only signal, and absence never authorizes stopping, abandoning, retrying or
releasing. `attention` (a permission prompt), `login`, `shell`, `gone` → report once with the handle (`❌ agent did not
finish — <state>`), never answer a prompt; `working` → `❌ still working after 90 min — terminal <handle>`, and the user
decides: keep waiting, or the fallback below. Count the waits as `waits=n` beside the handle in the state file. There is no
relaunch: `worker-stop` / `worker-abandon` only on positive proof the agent exited (an `exited` verdict, or a transcript
whose last turn sent no `worker_done`).

**kiro fallback → claude (always asked, never automatic).** A kiro submodule that ends `❌ agent did not start`,
`❌ agent did not finish — gone|login|shell`, `❌ agent hit its usage limit`, `❌ agent idle without worker_done`, or hit the 90-minute wait (and the `whoami` failure above) →
AskUserQuestion naming the submodule, the state, the terminal handle and — for a limit or idle stop — the git audit (commits found, dirty files): "Run `<NAME>` with claude instead?" (`whoami`
failure: the whole run) — `["Switch this submodule to claude", "Leave it ❌", "Retry kiro"]`. Non-interactive → leave it
`❌`. On a switch: release the failed kiro worker (`worker-release` — reclaimable after a failed start — or `worker-stop`
on proven exit; never `terminal close`; `worker-retain` instead if the user wants to read it — and always for a limit stop, whose kiro is still running), spawn a background
claude worker for that submodule on the same run (`worker-start --agent claude --model sonnet --effort medium` as above, brief as a file; no `whoami`), and
open its `BRIEF` with: "A previous agent may have left partial work on `<branch>` — run `git status` / `git log` first and
continue from it; don't redo or discard it." After a limit or idle stop, the brief also carries the audit: the commits found and the dirty files. Mark it `kiro → claude` in the state file; the other submodules stay on
kiro. `attention`, `❌ no commit`, `❌ not accepted` and `❌ dirty tree` are not offered a switch: the agent did run, so those go to the user as
they are.
**Idle close (3 minutes).** A `✅` worker nobody asks for again does not stay open on the user's machine:
1. When Step 6 has written the report, write `idle-since=<epoch seconds>` (`date +%s`) beside each `✅` worker's handle in the state file, then
   start one background `sleep 180` (Bash, `run_in_background: true`). Its notification is the wake-up. **Tell the user in the report** with one
   `Idle close:` line per `✅` handle — `Idle close: ✅ <handle> (<submodule>) at <HH:MM, `date -v+3M '+%H:%M'`> unless a new request reaches it` — so
   they know it will close and when; no `✅` worker → `Idle close: none`.
2. Any new request that reaches that terminal (`worker-start --terminal <handle>`, a fix after `/verify`, a follow-up brief) deletes its
   `idle-since` first: it is no longer idle, and it is reused like any idle terminal (*Reuse before create*).
3. At the wake-up, for every handle that still has `idle-since` (180 s or more old): `bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh"
   <handle> --once`. `SCREEN=agent` (an idle input box) → `ORCA orchestration worker-release --dispatch <id> --json` (it closes only that
   worker's own terminal, and the output stays readable with `worker-read`; never `terminal close`), then write `closed (idle 3 min)` in the
   state file, and **print one line**: `Idle close: closed <handle> (<submodule>) after 3 idle min`. Any other screen (`working`, `attention`, …) → leave it open, delete `idle-since`, and print one line: `Idle close: left open <handle> (<submodule>) — <screen state>`. A release that answers ok but leaves the terminal `retained` (the user touched it, `user_takeover`) is `left open`, not `closed`: check `worker-list` after the release before writing `closed`.
   `❌` terminals are never closed this way: they are retained for the user to read.

Record the handles in the state file; `❌` terminals stay open (`worker-retain`) for the user to read. Checkpoint with
`ORCA worktree set --worktree active --comment "assign <ticket>: wave N running (<names>)" --json`.
