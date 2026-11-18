# A worker agent's usage is measured now, never remembered

Whether kiro or claude can still take work is a fact of this minute. **Never** take it from a memory entry, a note, a state file, an earlier
run's result, or what a person said last week ("kiro is nearly out"): those are old the moment they are written. Measure it right before
the agent is chosen or started, and decide from that reading.

**When.** Before every start of a kiro or claude agent that does work: `orchestration worker-start`, `terminal create … --command claude|kiro-cli …`,
`agent launch`, `worktree create --agent claude`, and an `Agent` call that writes code or drives a browser for a brief (`/assign` agent mode,
`/verify` handing a check to an agent). Read-only `Agent` calls inside this session (reviewers, the briefing writer) run on this session's own
allowance: not a start. Starting a wave of workers needs one measurement per agent kind, taken just before the first start of the wave.

**How.** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/agent-usage.sh" kiro` or `… claude`. It runs the agent's own `/usage` (kiro: plan credits used of the plan,
reset date, overages; claude: current session % and week %, with their reset times) and prints `MEASURED <agent> <UTC time>` first. No `MEASURED`
line, exit 1 → not measured. Quote the figures in the line you report; the Orca terminals use the system-default account, which is the one measured.

**Decide from the reading.**
- The agent has room (below its limit) → use it, the default or the one `--agent` names. A high figure (kiro at 92%) is reported, not a reason to switch.
- The agent is spent (kiro: credits at or over the plan with overages disabled; claude: session or week at 100%, or a "limit reached" line):
  - the agent was named with `--agent` or by the user → stop and tell the user, with the figures; an explicit choice is never swapped;
  - the agent was the default → measure the other one; it has room → use it and say so in one line (`agent: claude — kiro credits 100%, measured <time>`); it is spent too → stop and tell the user;
  - a worker that stops *mid-task* on a limit stays `assign/orca-mode.md` *Another agent*: changing agent then is the user's decision.
- **Not measurable** (no `MEASURED` line): do not start the agent, do not guess from memory. Say what blocks (the command's own error, as printed), who opens it
  (the user: login, install, plan), and what was tried (`agent-usage.sh <agent>`, its exit code).

Eval: `evals/issue-agent-usage-measured-not-remembered`.
