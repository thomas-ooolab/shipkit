# Delegate implementation to Antigravity (via Orca)

Shared by `/spawn` (Step 5) and `/pr --implement` (Step 3). Implementation is done by the Antigravity
CLI (`agy`) in an Orca terminal — never by a Claude `Agent` call. Load the `orca-cli` skill and
resolve the executable as it says (`ORCA` below = that executable). Inputs per target: `PATH` (abs
submodule path, or repo root in single-repo mode), `NAME`, `BRIEF`.

> **Never-guess rule.** Terminal state (exists / idle / busy) comes from `orca terminal` output every
> run — handles go stale after an Orca restart. Send to exactly one handle per target.

## 1. Find or open the terminal (per target)
```text
ORCA terminal list --json
```
Candidate = `connected` terminal whose `agentIdentity` or `title` matches `antigravity|agy` and whose
`worktreePath` is `PATH` (or inside it). Idle check:
```text
ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 3000 --json
```
- `wait.satisfied: true` → reuse it (step 2).
- `false` → busy: `terminal read` the tail. Mid-task → never interrupt. Collect all busy targets and
  ask **once** (AskUserQuestion, Vietnamese): queue the brief anyway, or skip those targets.
- No candidate → open one:
  ```text
  ORCA terminal create --worktree active --title "agy-<ticket>-<NAME>" --command "cd <PATH> && agy" --json
  ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json
  ```
  Outside an Orca worktree drop `--worktree active`. `satisfied: false` → retry once with
  `--timeout-ms 120000`; still false, or `create` exits non-zero (e.g. `agy` not on PATH → quote the
  exact error) → target `❌ agy did not start`; **do not send** (input typed into a booting TUI is lost).

## 2. Send the brief
The brief must end with: "Finish by printing exactly one line: `✅ implemented <path> (N/M tasks)` or
`❌ <reason>`."
```text
ORCA terminal send --terminal <handle> --text "<brief>" --enter --wait-submit 10 --json
```
`accepted: true` = delivered. Never resend on silence; after a transport error repeat the exact command
with the reported `--retry-request <id>`. Sending to every target of a wave is parallel — no waiting
between targets.

## 3. Collect results
Per target, after `turn_started` is proven:
```text
ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 600000 --json
```
Repeat while `satisfied: false` (cap 6 rounds ≈ 60 min → `❌ timed out`). Then
`ORCA terminal read --terminal <handle> --json` and take the last `✅`/`❌` line; none → `❌ no result
line` with the tail attached. **Trust git, not the line:** confirm via `probe.sh state` that the feature
branch exists, is pushed (`unpushed=0`), and the tests the brief required were run.
