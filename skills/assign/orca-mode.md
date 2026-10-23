# /assign — Step 5, Orca mode (kiro and claude workers under Orca orchestration)

> Loaded by `/assign` in Orca mode, `AGENT=kiro` or `claude`. `BRIEF` and the wave plan are the ones SKILL.md built in Steps 1–5.

**Orca mode** (REQUIRED: load the `orca-cli` and `orchestration` skills first; `ORCA skills get orchestration` is the
version-matched guide). Same `BRIEF`, one worker per submodule, same wave order — only the agent's home and the plumbing
change: `/assign` is the **coordinator**; Orca creates and supervises each worker terminal (kiro or claude) itself and injects the brief.
**`AGENT=kiro` (the default, or the flag): run `kiro-cli whoami` first**, before starting a worker on a new terminal — "Not logged in" (or an
error) → start nothing and tell the user (in their language): "kiro is not logged in — run `! kiro-cli login`, then call
/assign", then offer the claude fallback (below) for the whole run instead of stopping dead. (Orchestration does not check
the login, and what a worker would show on a login screen was not verified — hence the check up front.)

**One Run per invocation.** Exactly one `ORCA orchestration run-create --objective "assign <ticket>" --json`, its id reused
for every wave and every `--run`, written to the state file (`run=<run_id>`). A second `run-create` from the same terminal
**fences** the first (`worker-start --run <old>` → `consumer_fenced`). A later `/assign` of the same ticket is a new
invocation → a new Run; terminals an older Run left are not reused (below): a new worker is started, its brief names the old handle.

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

**A settled terminal is never reused — every task gets a new worker.** Orca refuses `worker-start --terminal <handle>` for a terminal
whose worker has settled: `agent_unconfigured` — "Terminal <handle> is not running a recognized agent". Tested on a real Orca (1.4.237,
2026-10-23): a claude worker that had sent `worker_done` / `succeeded` (`SCREEN=agent`, `terminalState=reclaimable`, `terminal show` →
`agentIdentity: claude`, never retained) was refused with the call written `--spec … --terminal` **and** with Orca's own documented
`task-create` then `worker-start --task <id> --terminal`; an earlier test refused it after the ack, after a screen read and after minutes idle,
and `--terminal` with `--agent`, `--model` or `--effort` is refused for the flag itself. No state was found in which it is accepted, so the
coordinator **does not try it** — a failed call per follow-up buys nothing. Never confirmed to work for any agent kind (kiro, claude, codex, …).

A follow-up on a submodule that already has a worker — a later wave, a fix after `/verify`, a retry, a user-widened allowlist after a `❌` — is
a normal `worker-start --agent <AGENT>` below, on a new terminal. What the new worker needs is in git, not in the old terminal:
- Its `BRIEF` opens: "A previous worker (terminal `<handle>`) left N commits on `<branch>` — run `git status` and `git -C <PATH> log --oneline
  origin/<target>..HEAD` first and continue from them; don't redo or discard them. The allowlist below replaces the previous one." (N from
  that command; the previous summary's gap, e.g. the allowlist entry it lacked, goes in the brief too.)
- State file: the new line carries `previous=<old handle>` beside its own `terminal=`.
- The old terminal is not `working` (a second agent never goes on a `PATH` an agent is still working in: wait for its `worker_done` first). A
  settled `✅` one is `worker-release`d when the new worker starts (its idle close is moot); a `❌` one stays `worker-retain`ed for the user.
- A terminal recorded `unassigned` (a start that never reached a brief) holds no work: `worker-release` it, it is not handed to another submodule.

**Start the whole wave before waiting.** For every submodule in the wave:
1. `ORCA orchestration worker-start --spec "$(cat <brief file>)" --agent <AGENT> --worktree current --run <RUN> --json`
   A wave starts its workers in parallel (`&` then `wait` in one `bash -c`). The
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
  terminal's next owner, exactly one — never another brief (*A settled terminal is never reused*): a `❌` or not-accepted worker → **`worker-retain --dispatch <id>`** (the
  user reads what went wrong); a `✅` worker → left as it is and **closed on its own after 3 idle minutes** (*Idle close*
  below, which starts only in Step 6, after the last wave), or `worker-release` at once if the user asks or when a new worker for the same submodule starts. A settled terminal left undecided stays `reclaimable`.
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
**Idle close (3 minutes).** A `✅` worker does not stay open on the user's machine:
1. When Step 6 has written the report, write `idle-since=<epoch seconds>` (`date +%s`) beside each `✅` worker's handle in the state file, then
   start one background `sleep 180` (Bash, `run_in_background: true`). Its notification is the wake-up. **Tell the user in the report** with one
   `Idle close:` line per `✅` handle — `Idle close: ✅ <handle> (<submodule>) at <HH:MM, `date -v+3M '+%H:%M'`>` — so
   they know it will close and when; no `✅` worker → `Idle close: none`.
2. A new task for that submodule (a fix after `/verify`, a follow-up brief) starts a new worker, never a reuse: `worker-release` the old terminal
   and delete its `idle-since` then.
3. At the wake-up, for every handle that still has `idle-since` (180 s or more old): `bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-agent.sh"
   <handle> --once`. `SCREEN=agent` (an idle input box) → `ORCA orchestration worker-release --dispatch <id> --json` (it closes only that
   worker's own terminal, and the output stays readable with `worker-read`; never `terminal close`), then write `closed (idle 3 min)` in the
   state file, and **print one line**: `Idle close: closed <handle> (<submodule>) after 3 idle min`. Any other screen (`working`, `attention`, …) → leave it open, delete `idle-since`, and print one line: `Idle close: left open <handle> (<submodule>) — <screen state>`. A release that answers ok but leaves the terminal `retained` (the user touched it, `user_takeover`) is `left open`, not `closed`: check `worker-list` after the release before writing `closed`.
   `❌` terminals are never closed this way: they are retained for the user to read.

Record the handles in the state file; `❌` terminals stay open (`worker-retain`) for the user to read. Checkpoint with
`ORCA worktree set --worktree active --comment "assign <ticket>: wave N running (<names>)" --json`.
