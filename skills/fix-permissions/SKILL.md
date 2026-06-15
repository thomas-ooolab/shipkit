---
name: fix-permissions
description: Resolves and prints the terminal command that applies shipkit's permissions (the probe helper script + git/curl/test commands) to your Claude Code settings, clearing the "command requires approval" failure that blocks /bootstrap and the other skills' injected context — and unblocking /pr-from-plan's background agent. Works even when nothing is permitted yet; it never runs the applier itself. Run before /bootstrap. Not for app dependencies.
---

# shipkit · fix-permissions

One-command remediation for shipkit's permission gaps:

1. **Helper script.** Skills load context by auto-running `!`bash <plugin>/scripts/probe.sh …`` from
   the plugin install dir — outside your repo — so Claude Code wants approval on every skill load. An
   **injected** command can't show that prompt, so `/bootstrap` hard-fails *"command requires approval."*
2. **Background agent.** `/pr-from-plan --implement` runs its implementing agent non-interactively in
   an isolated worktree, so it **auto-denies** any un-allowlisted Bash. The applier writes shipkit's
   git/test command set to `~/.claude/settings.json` (`--user`) — the scope a background sub-agent reads.

This skill resolves the bundled applier's path and hands you the exact command to run.

> **Why it prints rather than runs:** a command **you** run in a terminal is your own action and is
> not subject to the injection/classifier block; a command the model runs is. Asking the model to run
> the applier would hit the very block this fixes (and `/bootstrap` is blocked at load for the same
> reason). So this skill resolves the path with read-only commands and gives it to you to run.

## Bounded scope
Points at the fix and (optionally, in default mode) runs the applier once with your confirmation. It
does not bootstrap, run probes, or touch app code. The applier only merges `permissions.allow`.

## Steps

1. **Resolve the applier.** Run `echo "${CLAUDE_PLUGIN_ROOT}/scripts/apply-permissions.sh"` (a
   read-only echo) to get the absolute path, then `test -f "<that path>"`.
   - Exists → that is `APPLIER`.
   - Missing → the installed plugin predates the script; tell the user to update
     (`/plugin marketplace update shipkit` then `/plugin install shipkit@shipkit`) and re-run, or use
     the self-resolving fallback in Step 2.

2. **Present the command.** Show the user, in a copy-pastable block, the exact command to run **in
   their own terminal** (default `--user` covers every project and the background-agent scope):

   ```bash
   bash "<APPLIER>" --user
   ```

   Also give the version/marketplace-independent self-resolving form (use when the path is unknown):

   ```bash
   bash "$(find ~/.claude/plugins -name apply-permissions.sh 2>/dev/null | sort -V | tail -1)" --user
   ```

   Note `--project` as the alternative (writes `<repo>/.claude/settings.json`, which you can commit
   so the whole team is unblocked on clone).

3. **Offer to run it (default mode only).** AskUserQuestion:
   `["Run it now, or copy it to run yourself?", "Run it now", "I'll run it myself"]`.
   - **Run it now** → execute `bash "<APPLIER>" --user` (one approval prompt in default mode). If it's
     denied, fall back to the printed command — the user must run it themselves.
   - **I'll run it myself** → stop after presenting the command.

4. **Verify.** Tell the user to confirm with `jq '.permissions.allow' ~/.claude/settings.json` — it
   should now include `Bash(bash:*)` (the probe) plus the git/curl/test rules. Then `/bootstrap` works.

## Error handling
- **Applier not found** (`test -f` fails): the installed plugin predates the script. Surface the
  update command and the self-resolving fallback; do not fabricate a path.
- **`${CLAUDE_PLUGIN_ROOT}` empty** (running outside plugin context): use the self-resolving `find`
  one-liner in Step 2.
- **Run-it-now denied**: report it plainly and direct the user to run the printed command themselves —
  that is the supported path, not a failure to retry.

## Gotchas
- `${CLAUDE_PLUGIN_ROOT}` is set in skill context but **not** in a plain user terminal — that's why
  the skill resolves the absolute path for the user rather than telling them to use the variable.
- Never instruct the user to ask Claude to run the applier as a normal step — it would be blocked by
  the same gap this remediates. The applier is designed to be run by the user.
- The applier is idempotent and backs up before writing; re-running is safe.

<example>
User: /fix-permissions
Assistant: [echoes ${CLAUDE_PLUGIN_ROOT}/scripts/apply-permissions.sh, confirms it exists]
"Run this in your terminal to apply shipkit's permissions (covers every project + background agents):

    bash \"/Users/you/.claude/plugins/cache/shipkit/shipkit/0.1.0/scripts/apply-permissions.sh\" --user

Then verify with `jq '.permissions.allow' ~/.claude/settings.json` and run `/bootstrap`. Want me to
run it now (default mode), or will you run it yourself?"
</example>
