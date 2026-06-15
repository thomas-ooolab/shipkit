#!/usr/bin/env bash
# apply-permissions.sh — one-shot remediation for shipkit's permission gaps.
#
# shipkit skills load context by auto-running `!bash <plugin>/scripts/probe.sh ...`. That script
# lives in the plugin install dir (outside your repo), so Claude Code prompts on every skill load —
# and an INJECTED command can't show that prompt, so /bootstrap hard-fails "command requires approval".
# Background/worktree agents (used by /pr-from-plan --implement) are non-interactive and auto-DENY
# any un-allowlisted Bash, so the pipeline's git/test commands must be allowed too.
#
# This writes shipkit's command allow-list to your Claude Code settings, fixing both.
#
# RUN IT YOURSELF — in your terminal, or via the Claude prompt's `!` prefix. Do NOT ask Claude to run
# it as a normal step: an injected/model-issued plugin-script command is the very thing this fixes
# (chicken-and-egg). A command YOU run is your own action, not the agent's.
#
# Idempotent: re-running makes no further change ("already up to date"). Backs up any file it changes
# and preserves every other key.
#
# Usage:
#   bash apply-permissions.sh [--user | --project] [--dir <project-dir>]
#     --user     (default) write ~/.claude/settings.json — covers EVERY project, and is the scope a
#                /pr-from-plan background worktree agent reads. Recommended.
#     --project  write <dir>/.claude/settings.json (commit it to share with the team).
#     --dir D    project dir for --project mode (default: current directory).
#
# Requires: jq.  Verify afterwards: jq '.permissions.allow' ~/.claude/settings.json
set -uo pipefail

MODE="user"; DIR="$(pwd)"
while [ $# -gt 0 ]; do
  case "$1" in
    --user)    MODE="user" ;;
    --project) MODE="project" ;;
    --dir)     shift; DIR="${1:-$(pwd)}" ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

command -v jq >/dev/null 2>&1 || { echo "error: jq is required (a shipkit dependency)" >&2; exit 1; }

# SSOT allow-list — everything shipkit's skills + background agents run.
#  Bash(bash:*)   the critical one: the injected probe runs as `bash "<plugin>/scripts/probe.sh" …`,
#                 and the plugin lives at a VERSIONED cache path, so a path-scoped rule would break
#                 on every update; bash:* matches regardless.
#  Bash(git:*)    branch create/checkout/push/commit/-C/rebase + read-only status/diff/log/submodule.
#  Bash(curl:*)   Bitbucket REST API (PRs, diffs, comments).
#  test runners   per-stack test cascade for /review-changes + /pr-from-plan --implement.
read -r -d '' ALLOW <<'JSON' || true
[
  "Bash(bash:*)",
  "Bash(git:*)",
  "Bash(curl:*)",
  "Bash(make:*)",
  "Bash(go:*)",
  "Bash(pytest:*)",
  "Bash(python:*)",
  "Bash(python3:*)",
  "Bash(npm:*)",
  "Bash(pnpm:*)",
  "Bash(yarn:*)",
  "Bash(node:*)",
  "Bash(flutter:*)",
  "Bash(dart:*)"
]
JSON

# Merge $want into .permissions.allow, de-duplicated; never touch other keys or "$defaults".
FILTER='($want) as $w
  | .permissions = (.permissions // {})
  | .permissions.allow = ((.permissions.allow // []) as $cur
      | $cur + [ $w[] | select(. as $x | ($cur | index($x)) | not) ])'

apply() {
  local f="$1" tmp existed=1
  if [ ! -f "$f" ]; then existed=0; mkdir -p "$(dirname "$f")"; printf '{}\n' > "$f"; fi
  jq empty "$f" 2>/dev/null || { echo "error: $f is not valid JSON — fix or remove it" >&2; return 1; }
  tmp="$(mktemp "${TMPDIR:-/tmp}/shipkit-perm.XXXXXX")"
  jq --argjson want "$ALLOW" "$FILTER" "$f" > "$tmp" || { rm -f "$tmp"; return 1; }
  if cmp -s "$f" "$tmp"; then echo "  = $f (already up to date)"; rm -f "$tmp"; return 0; fi
  [ "$existed" = 1 ] && cp "$f" "$f.bak-$(date +%Y%m%dT%H%M%S)"
  mv "$tmp" "$f"; echo "  + $f ($([ "$existed" = 1 ] && echo 'updated; backup written' || echo created))"
}

case "$MODE" in
  user)
    echo "Applying shipkit command permissions to user settings:"
    apply "$HOME/.claude/settings.json" || exit 1 ;;
  project)
    echo "Applying shipkit command permissions to project: $DIR"
    apply "$DIR/.claude/settings.json" || exit 1 ;;
esac
echo "Done. Re-run /bootstrap (then /run-pipeline <ticket>)."
