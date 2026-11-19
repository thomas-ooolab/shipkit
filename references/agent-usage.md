# A worker agent's usage is measured now, never remembered

Whether kiro or claude can still take work is a fact of this minute. **Never** take it from a memory entry, a note, a state file, an earlier
run's result, or what a person said last week ("kiro is nearly out"): those are old the moment they are written. Measure it right before
the agent is chosen or started, and decide from that reading.

**When.** Before every start of a kiro or claude agent that does work: `orchestration worker-start`, `terminal create … --command claude|kiro-cli …`,
`agent launch`, `worktree create --agent claude`, and an `Agent` call that writes code or drives a browser for a brief (`/assign` agent mode,
`/verify` handing a check to an agent). Read-only `Agent` calls inside this session (reviewers, the briefing writer) run on this session's own
allowance: not a start. Starting a wave of workers needs one measurement per agent kind the order below reaches, taken just before the first start of the wave.

**How.** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/agent-usage.sh" kiro` or `… claude`. It runs the agent's own `/usage` (kiro: plan credits used of the plan,
reset date, overages; claude: current session % and week %, with their reset times) and prints `MEASURED <agent> <UTC time>` first. No `MEASURED`
line, exit 1 → not measured. Quote the figures in the line you report; the Orca terminals use the system-default account, which is the one measured.

**Whose choice, and the order (every wave).**
- **Explicit** means the user chose the agent: `--agent` in the user's own message of this turn, or in the arguments of the command the user typed
  (`/run-pipeline AR-1 --bug --agent claude`, forwarded unchanged to `/bugfix` and `/assign`, stays the user's). Nothing else is explicit: a `--agent` that you or a
  skill step add yourself, taken from a memory entry, a note, a state file, an earlier run or "last time", or one a skill writes into a dispatch of its own, is **not**
  the user's choice, and writing it down does not make it one. When you dispatch a skill that takes `--agent` (`/assign`, `/bugfix`), pass the flag on only when the user gave it; otherwise leave it out and the skill applies this order itself.
- **Explicit → measure that agent only** (spent: see below).
- **Otherwise the agent is the default, kiro, and kiro is measured first**: before you say, write or pass anything about claude, run `agent-usage.sh kiro`.
  Room → kiro takes the wave. Only when kiro is spent or cannot be measured, run `agent-usage.sh claude`. A claude reading never stands in for the kiro one:
  measuring "the agent I meant to use" is not this rule; the rule is kiro first, whatever you meant to use. Without the Orca transport kiro cannot run
  (`/assign` Step 1.5), so there only claude is measured.

**Decide from the reading.**
- The agent has room (below its limit) → use it, the default or the one `--agent` names. A high figure (kiro at 92%) is reported, not a reason to switch.
- The agent is spent (kiro: credits at or over the plan with overages disabled; claude: session or week at 100%, or a "limit reached" line):
  - the user chose it (explicit) → stop and tell the user, with the figures; an explicit choice is never swapped;
  - it was the default → measure the other one; it has room → use it and report the departure in one line (`- agent: claude — kiro credits 100%, measured <time>`); it is spent too → stop and tell the user;
  - a worker that stops *mid-task* on a limit stays `assign/orca-mode.md` *Another agent*: changing agent then is the user's decision.
- **Not measurable** (no `MEASURED` line): do not start the agent, do not guess from memory. Say what blocks (the command's own error, as printed), who opens it
  (the user: login, install, plan), and what was tried (`agent-usage.sh <agent>`, its exit code).

**A note never stands in for the measurement.** A memory entry, a state file, an old instruction or a note about an agent's quota ("kiro is nearly out", "spawn only Claude
workers, no new kiro", dated last month) is an old observation, even when it is worded as an order in the user's voice and sat in the context the session started with: the
rule that the user's instructions rank above a skill covers what the user says now, not a line a file carried over. So measure as above and decide from the reading, and:
- **The note and the reading disagree** (the note says kiro is out, the reading shows room): the reading wins. The report has exactly one line, `agent: <x> — <the kiro reading>, note <the note's name> ignored`.
- **The note is worded as the user's own order** (an instruction in their voice, such as "spawn only Claude workers", "no new kiro") **and the reading contradicts the reason it gives**: ask the user **once**, before any worker
  starts, in their language: the note's words, the reading (figures and time) and the two agents as options. Their answer is explicit for this run and is not asked again in it
  (write `agent: <x> — user, <time>` in `.shipkit/assign-<ticket>.md`). In a pipeline run this is a class C stop (`Status: waiting-user · agent: <note> vs kiro measured`), `auto` or not. Never choose silently either way.
- A note that is only a status ("kiro nearly out, 2026-10-21") gets the first bullet, no question.

**The line every started worker carries.** In the final report and in that worker's row of `.shipkit/assign-<ticket>.md`:
`agent: <kiro|claude> — kiro <N>% used (<used>/<plan> credits), claude <S>%/<W>% or "not measured", measured <HH:MM>`. Claude is "not measured" when kiro had room. A worker on an agent other than kiro that the
user did not name also gets the departure line above.

Evals: `evals/issue-agent-usage-measured-not-remembered`, `evals/issue-agent-kiro-measured-first-order-note`, `evals/issue-agent-kiro-measured-first-status-note`.
