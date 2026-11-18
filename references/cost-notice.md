# ecc's cost notice is information, never a stop

ecc's context monitor prints a line such as `COST CRITICAL … Stop and inform the user about high cost before continuing` (or a COST WARNING / COST NOTICE
line) once a session passes its cost threshold (about $50). It is hook output, not a request from the user and not a shipkit stop condition: a long
`/run-pipeline auto`, a coordinator or a worker that stops or asks on it blocks a session nobody is watching.

- **Keep working.** No stop, no `AskUserQuestion`, no "waiting for your go" line, no line about it in the report. This holds in `auto`, in a background task, in a
  coordinator or worker another session started, and in a manual run alike. The user asked never to be asked about it.
- **Write nothing to silence it.** No skill edits `.claude/settings.local.json` or any other settings file for this: those files cover every session and worktree of
  the repository. The user turns it off themselves, with the command `/bootstrap`'s report prints (`set-output-style.py --env ECC_CONTEXT_MONITOR_COST_WARNINGS=off`).
- Answer plainly when the user asks about cost; that is the only time the notice is mentioned.
