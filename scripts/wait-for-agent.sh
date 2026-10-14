#!/usr/bin/env bash
# wait-for-agent.sh — block until the coding agent in an Orca terminal (kiro or claude) has finished
# its turn, deciding from what is ON SCREEN, not from a magic final line. Run via
# Bash(run_in_background:true) to get ONE notification when it ends, instead of grepping the screen
# for an exact "✅ implemented" that an agent may never print (kiro finishes in plain prose).
#
#   usage: wait-for-agent.sh <terminal-handle> [--timeout-s 1800] [--poll-s 10] [--git <submodule-path> <branch>]
#
# Polls `orca terminal read --terminal <handle> --screen --json` (ORCA resolved the way the orca-cli
# skill's stub says) and classifies the bottom of the screen:
#   WORKING  kiro "Thinking...", "esc to cancel", "Kiro is working", a "• Shell" line with no result yet;
#            claude "esc to interrupt" or a spinner line ("✢ Frosting… (1m 19s · …)")
#   READY    kiro "ask a question or describe a task"; claude's "❯" input line inside its prompt box
#   DONE     READY and no WORKING for 2 polls in a row
# `terminal wait --for tui-idle` alone is not enough — a bare shell or a login/model error screen is
# idle too, so those are told apart here. It only READS: it never sends input or answers a prompt.
#
# Output (stdout): STATE=, PUSHED=, CLEAN= (plus BRANCH= with --git), then the last ~30 screen lines.
# PUSHED/CLEAN are `na` unless --git was given and the state is `done`; with --git, after DONE it
# reports the checked-out branch, whether `git ls-remote --heads origin <branch>` equals local HEAD
# (pushed) and whether the working tree is clean — trust git, not the agent's last line.
#
# exit 0  STATE=done      the agent's prompt is back and it is idle
# exit 2  STATE=timeout   still working (or unclear) after --timeout-s — relaunch to keep waiting
# exit 3  STATE=gone      terminal closed/orphaned/stale handle (or orca unreachable 3 reads in a row)
# exit 4  STATE=login     "Not logged in" / "isn't available" on screen with no agent UI
# exit 5  STATE=shell     no agent UI for 3 polls in a row — fell back to a shell prompt
# exit 6  STATE=attention agent is stopped on a y/n or numbered permission prompt — a person answers it

set -uo pipefail

USAGE="usage: wait-for-agent.sh <terminal-handle> [--timeout-s 1800] [--poll-s 10] [--git <submodule-path> <branch>]"
HANDLE="${1:?$USAGE}"; shift
TIMEOUT_S=1800; POLL_S=10; GIT_PATH=""; GIT_BRANCH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --timeout-s) TIMEOUT_S="${2:?$USAGE}"; shift 2 ;;
    --poll-s)    POLL_S="${2:?$USAGE}"; shift 2 ;;
    --git)       GIT_PATH="${2:?$USAGE}"; GIT_BRANCH="${3:?$USAGE}"; shift 3 ;;
    *) echo "$USAGE" >&2; exit 64 ;;
  esac
done

if [ -n "${ORCA_CLI_COMMAND:-}" ]; then ORCA="$ORCA_CLI_COMMAND"
elif [ -n "${ORCA_DEV_REPO_ROOT:-}" ]; then ORCA="orca-dev"
elif [ "$(uname -s)" = "Linux" ]; then ORCA="orca-ide"
else ORCA="orca"; fi

body_file=$(mktemp); screen_file=$(mktemp)
trap 'rm -f "$body_file" "$screen_file"' EXIT

finish() { # <state> <exit> [pushed] [clean] [branch]
  echo "STATE=$1"; echo "PUSHED=${3:-na}"; echo "CLEAN=${4:-na}"
  [ -n "${5:-}" ] && echo "BRANCH=$5"
  echo "--- last screen lines (terminal $HANDLE)"
  tail -n 30 "$screen_file"
  exit "$2"
}

deadline=$(( $(date +%s) + TIMEOUT_S ))
ready_n=0; none_n=0; login_n=0; attn_n=0; fail_n=0

while :; do
  # stderr stays out of the way; a failed read is judged below and its payload is never printed
  "$ORCA" terminal read --terminal "$HANDLE" --screen --json >"$body_file" 2>/dev/null
  # Program on stdin, data as argv files (a `python3 -` heredoc consumes stdin for the program itself).
  verdict=$(python3 - "$body_file" "$screen_file" <<'PY'
import json, re, sys
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
except Exception:
    print("FAIL"); sys.exit()
if not d.get("ok"):
    code = str((d.get("error") or {}).get("code", ""))
    print("GONE" if re.search(r"stale|not_found|gone|closed|orphan", code) else "FAIL"); sys.exit()
t = d["result"]["terminal"]
lines = [l.replace("\xa0", " ").rstrip() for l in t.get("tail", [])]
open(sys.argv[2], "w").write("\n".join(lines) + "\n")
if t.get("status") not in (None, "running"):
    print("GONE"); sys.exit()
live = [l for l in lines if l.strip()]
tail = live[-14:]
blob = "\n".join(tail)

def running_shell():  # last "• " bullet is a Shell call whose only lines since are "╰ …" (no result yet)
    foot = re.compile(r"^[\s─]*$|Trust All Tools|^Default ·|ask a question|/sessions to resume|Credits:|What's new|^\(.*\)$")
    i = len(live) - 1
    while i >= 0 and foot.search(live[i]):
        i -= 1
    while i >= 0 and re.match(r"^\s*╰", live[i]):
        i -= 1
    return i >= 0 and live[i].startswith("• Shell")

working = (re.search(r"Thinking\.\.\.|esc to cancel|esc to interrupt|Kiro is working", blob)
           or re.search(r"^\s*\S\s+\S+…\s*\(\d+[ms]", blob, re.M)
           or running_shell())
attn = re.search(r"\(y/n\)|\[y/N\]|\[Y/n\]|^\s*❯\s*1\.\s", blob, re.M)
ready = bool(re.search(r"ask a question or describe a task", blob)) or any(
    re.match(r"^\s*❯", l) and i > 0 and "──" in tail[i - 1] for i, l in enumerate(tail))
login = re.search(r"Not logged in|isn't available|is not available|not available|login required", "\n".join(live[-20:]), re.I)

if working: print("WORKING")
elif attn: print("ATTENTION")
elif ready: print("READY")
elif login: print("LOGIN")
else: print("NONE")
PY
  ) || verdict=FAIL

  case "$verdict" in
    GONE) finish gone 3 ;;
    FAIL) fail_n=$((fail_n + 1)); [ "$fail_n" -ge 3 ] && finish gone 3 ;;
    WORKING)   fail_n=0; ready_n=0; none_n=0; login_n=0; attn_n=0 ;;
    ATTENTION) fail_n=0; ready_n=0; none_n=0; attn_n=$((attn_n + 1)); [ "$attn_n" -ge 2 ] && finish attention 6 ;;
    LOGIN)     fail_n=0; ready_n=0; none_n=0; login_n=$((login_n + 1)); [ "$login_n" -ge 2 ] && finish login 4 ;;
    NONE)      fail_n=0; ready_n=0; none_n=$((none_n + 1)); [ "$none_n" -ge 3 ] && finish shell 5 ;;
    READY)
      fail_n=0; none_n=0; login_n=0; attn_n=0; ready_n=$((ready_n + 1))
      if [ "$ready_n" -ge 2 ]; then
        if [ -n "$GIT_PATH" ]; then
          head_branch=$(git -C "$GIT_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
          head_sha=$(git -C "$GIT_PATH" rev-parse HEAD 2>/dev/null || echo "-")
          remote_sha=$(git -C "$GIT_PATH" ls-remote --heads origin "$GIT_BRANCH" 2>/dev/null | cut -f1 | head -n1)
          pushed=no; [ "$head_branch" = "$GIT_BRANCH" ] && [ -n "$remote_sha" ] && [ "$remote_sha" = "$head_sha" ] && pushed=yes
          clean=no; [ -z "$(git -C "$GIT_PATH" status --porcelain 2>/dev/null)" ] && clean=yes
          finish done 0 "$pushed" "$clean" "$head_branch"
        fi
        finish done 0
      fi
      ;;
  esac

  [ "$(date +%s)" -ge "$deadline" ] && finish timeout 2
  sleep "$POLL_S"
done
