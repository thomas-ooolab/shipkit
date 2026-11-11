# /assign — Step 5, Orca mode (kiro and claude workers under Orca orchestration)

> Loaded by `/assign` in Orca mode, `AGENT=kiro` or `claude`. `BRIEF` and the wave plan are the ones SKILL.md built in Steps 1–5.

**Orca mode** (REQUIRED: load the `orca-cli` and `orchestration` skills first; `ORCA skills get orchestration` is the
version-matched guide). Same `BRIEF`, one worker per submodule, same wave order — only the agent's home and the plumbing
change: `/assign` is the **coordinator**; Orca supervises each worker terminal (kiro or claude) and injects the brief. Orca launches a claude worker itself; for kiro
the coordinator opens the terminal first (*Starting kiro*), because `worker-start --agent kiro` hands the brief over too early.
**`AGENT=kiro` (the default, or the flag): run `kiro-cli whoami` first**, before starting a worker on a new terminal — not logged in (or an
error) → start nothing; tell the user, in their language, that kiro is not logged in and that `! kiro-cli login` fixes it, and put the
claude fallback (below) to them for the whole run instead of stopping dead. (Orchestration does not check
the login, and what a worker would show on a login screen was not verified — hence the check up front.)

**Judge, don't match.** Nothing below is a pattern table. A screen line, a `SCREEN=` value, a banner or one failed read is a *lead*: it
tells you where to read next, never what to conclude or what to ask the user. Every call about a worker — working, blocked, broken, done —
is yours, made from the evidence in *Reading a worker*, and a report or a question to the user cites that evidence (which commits, which
files changed since the last look, which transcript turn, which message). Wording of reports and questions is never fixed: say what was
found, what you decided and why and — only when it is the user's call — what the choices are, in the language the user writes in.
The invariants that do not bend: workers never push; a permission prompt is never answered on the user's behalf, except kiro's workspace-trust prompt under every condition of
*Kiro's trust prompt* below; stop, abandon or retry
only on positive proof the process exited; one Run per invocation; a settled terminal is never reused; a brief never goes in with
`terminal send`.

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
  reply. A permission prompt on a terminal is never answered on the user's behalf (the one exception: *Kiro's trust prompt*).
- **UI task:** the `Design` bullet of the `BRIEF` applies; the `worker_done` summary says the 1-to-1 comparison was done, or names the
  differences left. Once that worker settles, or is stopped, run `scripts/cleanup-browsers.sh` on its scratch directory (SKILL.md, *Design*).

**A settled terminal is never reused — every task gets a new worker.** Orca refuses `worker-start --terminal <handle>` for a terminal
whose worker has settled: `agent_unconfigured` — "Terminal <handle> is not running a recognized agent". Tested on a real Orca (1.4.237,
2026-10-23): a claude worker that had sent `worker_done` / `succeeded` (`SCREEN=agent`, `terminalState=reclaimable`, `terminal show` →
`agentIdentity: claude`, never retained) was refused with the call written `--spec … --terminal` **and** with Orca's own documented
`task-create` then `worker-start --task <id> --terminal`; an earlier test refused it after the ack, after a screen read and after minutes idle,
and `--terminal` with `--agent`, `--model` or `--effort` is refused for the flag itself. No state was found in which it is accepted, so the
coordinator **does not try it** — a failed call per follow-up buys nothing. Never confirmed to work for any agent kind (kiro, claude, codex, …). A kiro *warm
terminal* (*Starting kiro*) is not that case: it has never had a worker, and `worker-start --terminal` on it is the route that works.

A follow-up on a submodule that already has a worker — a later wave, a fix after `/verify`, a retry, a user-widened allowlist after a `❌` — is
a normal `worker-start --agent <AGENT>` below, on a new terminal. What the new worker needs is in git, not in the old terminal:
- Its `BRIEF` opens: "A previous worker (terminal `<handle>`) left N commits on `<branch>` — run `git status` and `git -C <PATH> log --oneline
  origin/<target>..HEAD` first and continue from them; don't redo or discard them. The allowlist below replaces the previous one." (N from
  that command; the previous summary's gap, e.g. the allowlist entry it lacked, goes in the brief too.)
- State file: the new line carries `previous=<old handle>` beside its own `terminal=`.
- The old terminal is not `working` (a second agent never goes on a `PATH` an agent is still working in: wait for its `worker_done` first). A
  settled `✅` one is `worker-release`d when the new worker starts (its idle close is moot); a `❌` one stays `worker-retain`ed for the user.
- A terminal recorded `unassigned` (a start that never reached a brief) holds no work: `worker-release` it, it is not handed to another submodule.

**The user asks to "reuse" a worker or terminal** ("reuse worker", "use the same terminal"): say once, in their language, that Orca refuses it for a
settled worker and the work continues in a new worker, then start that worker as above — never call `--terminal` to show it. Edits an old worker
left uncommitted stay in the working tree, so the new brief says to run `git status` first and keep them.

**Start the whole wave before waiting.** For every submodule in the wave:
1. **claude:** `ORCA orchestration worker-start --spec "$(cat <brief file>)" --agent claude --worktree current --run <RUN> --model sonnet --effort medium --json`
   (implementing a brief is routine coding). **kiro:** open a warm terminal first (*Starting kiro*), then `ORCA orchestration worker-start --spec "$(cat <brief file>)"
   --terminal <handle> --worktree current --run <RUN> --json` — no `--agent`, `--model` or `--effort` (refused together with `--terminal`; kiro runs with the model of its own
   config, and the CLI takes those flags only for Claude, Codex, Cursor, Antigravity and Muse). A wave starts its workers in parallel (`&` then `wait` in one `bash -c`).
   The agent shares this checkout and owns only its `PATH`, as in Agent mode. Always `--worktree current` — never `worktree
   create` (a second checkout `probe.sh` can't see) — and never `dispatch --inject` or a brief sent with
   `terminal send`. A brief never lands in a shell: Orca launches a claude worker itself, and for kiro it injects only into a terminal it recognises as kiro.
2. Read the receipt: `taskId`, `dispatchId`, `state: ready`, `stage: input_accepted`, `turnStart` (`unsupported` for kiro, `observed` for claude). The
   terminal handle is `worker-show --dispatch <id>` → `worker.agentTerminalHandle`. **`input_accepted` is not proof the
   agent took the brief** (Orca cannot observe kiro's turn; for claude `turnStart: observed` already is the confirmation), so for kiro make **one** read-only confirmation with *Reading a worker*:
   the worker's first message in `check`, the transcript starting to show the brief, or the tree beginning to change (a screen read a few times, 5 s apart, is
   one input). A worker that shows no sign of having taken the brief after you have read those, and whose terminal is at a shell, a login
   screen or gone, did not start; anything short of that is a checkpoint to read again, never a resend.
3. `worker-start` **non-zero** (or `ok: false`) → the worker did not start: report it with the receipt's `error.code` /
   `failedStage` / `residualResources`. A refusal before any launch (e.g. `agent_unconfigured`) leaves nothing behind. A
   start that launched leaves a terminal owned by that worker (`worker-list` shows it `reclaimable`): release it with
   `worker-release` (or, if the user wants to read it, `worker-retain` and record it `unassigned`) — never `terminal close` — and retry only with `--task <id> --retry-of <dispatch>`, never a blind
   relaunch. The retry carries no `--spec`: `--task` and `--spec` are mutually exclusive (`invalid_argument`); the task already holds the brief. A kiro start that
   failed on `agent_not_in_foreground` or `agent-trust-workspace` is *Starting kiro* below — never a second or third `--agent kiro`. Orca allows a Task 3 failed starts; the third locks it
   (`task_not_startable`), so a retry is for a cause you have understood, not for waiting. (Other failures after launch were not reproduced; this follows the recovery reference.)
4. Record per submodule in the state file: `task=<id> dispatch=<id>` beside the handle, kind and submodule.

**Starting kiro — a warm terminal, then the brief. Never `worker-start --agent kiro`.** Why (AR-688, 2026-11-11, Orca 1.4.x; traced in Orca's code and reproduced):
`--agent kiro` opens a terminal, types `kiro-cli chat --tui --trust-all-tools --v3` and injects the brief at once, while kiro V3 still shows "Initializing…" (its
kiro-cli → kiro-cli-chat → bun process tree takes several seconds to settle). The injection needs Orca to see kiro in the foreground, and on POSIX only that verdict
passes — `unknown` or `shell` fails with `failedStage: dispatch_input`, `lastError: agent_not_in_foreground`. Orca allows 3 failed starts per Task and the third locks it
(`task_not_startable`: "failed 3 times … Do not retry this Task or start a replacement"); AR-688 spent all three, two of them on retries of this same timing failure.
Orca does not misread kiro: a terminal opened with `terminal create` and left about 10 s reports `agentIdentity: kiro` at kiro's input box. The brief only arrived too early.

For each kiro worker, before `worker-start`:
1. `ORCA terminal create --worktree current --title "<ticket> kiro" --command "kiro-cli chat --tui --trust-all-tools --v3" --json` → the handle (the command Orca itself typed in
   AR-688). Write it to the state file as `terminal=<handle> (kiro, warm terminal)` and `unassigned` until the brief is in.
2. Wait until kiro's input box is up and "Initializing…" is gone — read `ORCA terminal read --terminal <handle> --screen --json` every few seconds (AR-688 took about 10 s;
   `wait-for-agent.sh <handle> --once` is a hint, and `terminal show` reporting `agentIdentity: kiro` is a second sign). "Trust this workspace?" is *Kiro's trust prompt* below.
   **The wait happens here, never inside retries** — each failed start costs one of Orca's 3. A terminal that is still not at an input box after a good while (a shell prompt with the command
   typed, an error, a login screen) did not start: read it, tell the user as with any start failure, and close the terminal you created (`terminal close --terminal <handle>`; it never had a
   worker, so there is nothing to `worker-release` — not verified).
3. `worker-start --spec … --terminal <handle>` as in step 1; read the receipt (`state: ready`) and confirm with step 2 of the list above (one screen read after about 10 s shows kiro reading the brief).
   A failure here is judged like any start failure (step 3), from the receipt and the screen.

A Task Orca has locked (`task_not_startable`) is neither retried nor replaced under that Task: release its residual terminal, then run this route again with a new warm terminal and `worker-start --spec`
(a new Task), the brief opening as a follow-up (*A follow-up on a submodule*). That is what finished AR-688, although Orca's message says not to start a replacement — tell the user in one line that you did.

*Verified in AR-688:* this route took the brief, the worker sent `worker_done` / `succeeded` and left a clean commit. *Not verified:* the route with several kiro workers in one wave
(one warm terminal each — start them the same way and judge each from its own screen); where `--v3` comes from (not in Orca's code, `kiro-cli --version` 2.35.1 — probably kiro's own config);
the same route on a host where Orca types another kiro command.

**Kiro's trust prompt — the one prompt the coordinator answers.** A folder kiro has not trusted shows, on first use only, "Trust this workspace?", a folder path, a warning that the folder can
hold hooks, agents, MCP servers and workflows that run commands, and one option, "Trust, continue". The warm terminal meets it before any brief is handed over. Answer it yourself **only when
all of these hold**, each read, not assumed:
- the terminal is the warm terminal you created in this invocation (or the residual terminal of a failed `--agent kiro` start whose receipt had `failedStage: agent_readiness` and
  `lastError: Agent startup blocked: agent-trust-workspace`);
- its screen (`ORCA terminal read --terminal <handle> --screen --json`) shows "Trust this workspace?", a folder path **exactly equal** to the path `ORCA worktree current --json` gives
  (a path the screen wraps or shortens is not equal), and the "Trust, continue" option.

Then send `ORCA terminal send --terminal <handle> --text "" --enter` and read the screen once — it should move on ("Initializing…", then kiro's input box) — and carry on with the wait of
step 2 above. For a residual terminal of a failed start: `worker-release --dispatch <id>`, then use the warm route with a new terminal (trust now persists), never `--agent kiro` again.
A screen that did not move after the Enter goes to the user with the screen lines. Any other prompt, any other option, a folder that differs, or anything unread is **not answered**: put it to the
user as with every other permission prompt. Never press a bare Enter on a kiro menu you have not read — a fresh `kiro-cli` showed a "Switch to V3" menu whose first option rewrites the user's configs.
Tell the user in one line which folder was trusted for kiro. *Verified 2026-11-09:* Enter sent with `terminal send` moves the prompt on in a terminal made with `ORCA agent launch --agent kiro`, and the trust
persisted for the folder. *Not verified:* the same Enter in a terminal made with `terminal create --command`, or in the residual terminal of a failed start — if the screen does not move, that is the user's.
claude workers showed no trust prompt (they run in bypass-permissions mode): nothing to add for them.

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
  hint, then from the commit and the spec's tasks); no commit, a dirty tree, or a worker that pushed
  anyway (`unpushed=0` before you pushed) → `❌`, say which — report it, don't accept on top. **Either outcome**, then the
  terminal's next owner, exactly one — never another brief (*A settled terminal is never reused*): a `❌` or not-accepted worker → **`worker-retain --dispatch <id>`** (the
  user reads what went wrong); a `✅` worker → left as it is and **closed on its own after 3 idle minutes** (*Idle close*
  below, which starts only in Step 6, after the last wave), or `worker-release` at once if the user asks or when a new worker for the same submodule starts. A settled terminal left undecided stays `reclaimable`.
- **`escalation`** → Orca's own note that something went wrong (for instance that a worker ended its turn on an error without `worker_done`). It is
  evidence, not a verdict: read the worker as in *Reading a worker*, answer nothing on the user's behalf, and tell the user what you found and
  decided — or the choice, if it is theirs. (This message type was not reproduced.)
- Then `ORCA orchestration check --run <RUN> --ack <delivery_id> --wait --types worker_done,escalation,question
  --timeout-ms 600000 --json` acks and waits for the next one in one call.
Wait for the **whole wave** to settle before starting the next — a later wave may depend on what an earlier one just
accepted (e.g. FE reading BE's freshly generated types). Before the turn ends, `ORCA orchestration worker-list --run <RUN>
--terminal-state reclaimable --json` must be empty, except the `✅` terminals whose idle close is pending.

## Reading a worker

`check --wait` returns nothing while a worker is busy, stuck, blocked or dead alike, so every empty wait (10 minutes) is an occasion to
read each worker not yet settled — read-only: nothing is sent, nothing is killed. Take the evidence that fits, from what you can see
without touching the worker:
- **Transcript** — `worker-read` for the dispatch: what its last turns did, whether it is mid-task, asked something, hit an error, or
  said it was done.
- **The tree** — `git -C <PATH> status --short` and `git -C <PATH> log --oneline origin/<target>..HEAD`, compared with the previous look
  (which files changed since, which commits landed). Changing files are the strongest sign of work in progress; an unchanged tree is a
  weak sign by itself (a worker may be reading or thinking).
- **Orca** — the worker's messages and escalations (`check`), `worker-list` / `worker-show` (heartbeat, terminal state; for kiro the
  liveness is `unverifiable`, so its silence proves nothing), `terminal show`.
- **The screen** — `wait-for-agent.sh <handle> --once` classifies it as a hint (`working`, `agent` for an idle input box, `attention`,
  `login`, `limit`, `shell`, `unknown`, `gone`). It matches fixed patterns, so it is wrong about what it has not seen before; read the
  screen lines it prints yourself.

Then **conclude one of these, with the evidence**, and act on it:
- **Working** — the tree or the transcript is moving, or the agent is visibly in a turn. Keep waiting.
- **Blocked** — it is stopped on something a person or the coordinator can answer: a permission prompt (never answered for the user, bar *Kiro's trust prompt*), a
  `question` or `ask`, an allowlist gap it named. Answer per the rules above, or put it to the user.
- **Done but silent** — the work is on the branch and the agent is idle without having sent `worker_done`. Audit it as a `worker_done`
  (*Accept, then push*); the missing report is a note, not a failure, when git shows the tasks done.
- **Stopped without finishing** — no progress between looks, an idle or dead terminal, and a transcript that ended (on an error, a spent
  quota, or nothing) with the tasks undone. Report what it left (commits, dirty files) and what the transcript says ended it.
- **Cannot tell yet** — say so, say which look would settle it, and read again at the next wait. This is a checkpoint, not a failure.

**One line is not a verdict.** A banner or notice (a model unavailable, tools disabled, a config fetch failed) beside a live input box can
be printed by a worker that is working normally, and one idle look can be a worker between turns. What decides is whether work moves —
the tree, the transcript — and what the transcript says ended a turn. A worker that really stopped on an error looks the same on screen as one that was
only slow, which is why you read the tree and the transcript before you call it, and before you ask the user anything.

**Long quiet.** There is no wait count that turns silence into a failure. The more waits pass with no movement, the more the reading
should go to the transcript and the tree, and the sooner the user hears — once, with the evidence and what you will do next (keep waiting,
or the options below). Count the waits as `waits=n` beside the handle in the state file. There is no relaunch: `worker-stop` /
`worker-abandon` only on positive proof the agent exited — an `exited` verdict from Orca, a terminal gone or sitting at a shell prompt, or
a transcript whose last turn ended without `worker_done` while the screen stays idle across looks.

**When a worker stopped without finishing — your options.** Audit first (commits, dirty files), then choose from the evidence:
- *The same agent again*: a new worker on the same submodule (a settled terminal is never reused) with the audit in its brief, when the
  process is proven exited and nothing is lost on the branch. One retry is yours to make and to tell the user about; the same failure again
  goes to the user with both attempts' evidence.
- *Another agent*: changing agent is the user's decision — put it to them with the evidence (login failed, quota spent, repeated stops,
  never started) when it is what the evidence points to, never because one line looked bad. Non-interactive → leave the submodule failed.
- *Neither*: the work stopped for a reason a different agent will not change (an allowlist gap, an unclear task, a failing test in the
  worker's scope) — that goes to the user as it is.
On a switch to claude, release the stopped kiro worker (`worker-release` — reclaimable after a failed start — or `worker-stop` on proven
exit; never `terminal close`; `worker-retain` instead if the user wants to read it, and always when the kiro is still running), start a
claude worker for that submodule on the same Run (`worker-start --agent claude --model sonnet --effort medium` as above, brief as a file; no
`whoami`), and open its `BRIEF` the way a follow-up opens (*A settled terminal is never reused*): partial work may be on `<branch>`, run
`git status` / `git log` first and continue from it, plus the audit's commits and dirty files. Mark it `kiro → claude` in the state file; the
other submodules stay on kiro.

**Idle close (3 minutes).** A `✅` worker does not stay open on the user's machine:
1. When Step 6 has written the report, write `idle-since=<epoch seconds>` (`date +%s`) beside each `✅` worker's handle in the state file, then
   start one background `sleep 180` (Bash, `run_in_background: true`). Its notification is the wake-up. **Tell the user in the report** with an
   `Idle close:` line: which `✅` terminals will close and at what time (`date -v+3M '+%H:%M'`), or that none will.
2. A new task for that submodule (a fix after `/verify`, a follow-up brief) starts a new worker, never a reuse: `worker-release` the old terminal
   and delete its `idle-since` then.
3. At the wake-up, for every handle that still has `idle-since` (180 s or more old), read it (*Reading a worker*; the screen look and the
   transcript). It is idle — an input box, nothing in progress — → `ORCA orchestration worker-release --dispatch <id> --json` (it closes only that
   worker's own terminal, and the output stays readable with `worker-read`; never `terminal close`), then write `closed (idle 3 min)` in the
   state file. It is doing something, or waiting on a person (a prompt, a question) → leave it open and delete `idle-since`. A release that answers
   ok but leaves the terminal `retained` (the user touched it, `user_takeover`) is left open, not closed: check `worker-list` after the release
   before writing `closed`. Tell the user in one line per handle what you did and why (closed, or left open and what it was doing) — an
   `Idle close:` line. `❌` terminals are never closed this way: they are retained for the user to read.

Record the handles in the state file; `❌` terminals stay open (`worker-retain`) for the user to read. Checkpoint with
`ORCA worktree set --worktree active --comment "assign <ticket>: wave N running (<names>)" --json`.
