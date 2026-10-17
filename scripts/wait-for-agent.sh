#!/usr/bin/env bash
# wait-for-agent.sh <terminal-handle> --once — one read-only look at an Orca terminal: is a coding agent (kiro or
# claude) idle, working, stopped on a prompt, or gone? It decides from what is ON SCREEN, not from a magic string, and
# it only READS: it never sends input or answers a prompt.
#
#   usage: wait-for-agent.sh <terminal-handle> --once
#
# Reads `orca terminal read --terminal <handle> --screen --json` (ORCA resolved the way the orca-cli skill's stub
# says) and classifies the bottom of the screen:
#   WORKING  kiro "Thinking...", "esc to cancel", "Kiro is working", a "• Shell" line with no result yet;
#            claude "esc to interrupt" or a spinner line ("✢ Frosting… (1m 19s · …)")
#   READY    an input box on screen — two horizontal rules (────) a few lines apart near the bottom, which is how
#            both kiro (v3 shows no "ask a question…" text) and claude draw theirs; the old kiro string and claude's
#            "❯" line under a rule still count. Background status lines ("What's new", "Fetching your cloud config")
#            are neither WORKING nor a blocker: the agent can already chat.
# `terminal wait --for tui-idle` alone is not enough — a bare shell or a login/model error screen is idle too, so
# those are told apart here.
#
# Output (stdout): SCREEN=<value>, then the last ~30 screen lines.
#   SCREEN=agent      an input box is up, nothing working — idle
#   SCREEN=working    the agent is working
#   SCREEN=attention  stopped on a y/n or numbered permission prompt — a person answers it
#   SCREEN=login      "Not logged in" / "isn't available" with no agent UI
#   SCREEN=shell      no agent UI and the last line looks like a shell prompt
#   SCREEN=unknown    nothing recognisable yet (TUI still drawing, or an unfamiliar screen) — read again
#   SCREEN=gone       terminal closed / stale handle / orca unreachable (exit 3)
# exit 0 for every SCREEN except gone (exit 3); exit 64 on bad usage.

set -uo pipefail

USAGE="usage: wait-for-agent.sh <terminal-handle> --once"
HANDLE="${1:?$USAGE}"; shift
[ "${1:-}" = "--once" ] && [ $# -eq 1 ] || { echo "$USAGE" >&2; exit 64; }

if [ -n "${ORCA_CLI_COMMAND:-}" ]; then ORCA="$ORCA_CLI_COMMAND"
elif [ -n "${ORCA_DEV_REPO_ROOT:-}" ]; then ORCA="orca-dev"
elif [ "$(uname -s)" = "Linux" ]; then ORCA="orca-ide"
else ORCA="orca"; fi

body_file=$(mktemp); screen_file=$(mktemp)
trap 'rm -f "$body_file" "$screen_file"' EXIT

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
    foot = re.compile(r"^[\s─]*$|Trust All Tools|^Default ·|ask a question|/sessions to resume|Credits:|What's new|Fetching|^\(.*\)$")
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
# Input box = two horizontal rules, up to a few lines apart (an empty input line is blank, so 0 lines between counts), ending within the last few lines. No agent-
# specific text is needed; the strings below are kept only as extra evidence for older screens.
rules = [i for i, l in enumerate(live) if re.search(r"[─━]{8,}", l)]
box_top = None
for a, b in reversed(list(zip(rules, rules[1:]))):
    if 1 <= b - a <= 6 and b >= len(live) - 6:  # blank input line is not in `live`: adjacent rules still count
        box_top = a
        break
ready = box_top is not None or bool(re.search(r"ask a question or describe a task", blob)) or any(
    re.match(r"^\s*❯", l) and i > 0 and "──" in tail[i - 1] for i, l in enumerate(tail))
shell = bool(live) and re.search(r"[$%#>»➜❯]\s*$", live[-1]) is not None
login = re.search(r"Not logged in|isn't available|is not available|not available|login required", "\n".join(live[-20:]), re.I)

if working: v = "WORKING"
elif attn: v = "ATTENTION"
elif ready: v = "READY"
elif login: v = "LOGIN"
elif shell: v = "SHELL"
else: v = "NONE"
print(v)
PY
) || verdict=FAIL

case "$verdict" in
  WORKING) screen=working ;; ATTENTION) screen=attention ;; READY) screen=agent ;;
  LOGIN) screen=login ;; SHELL) screen=shell ;; NONE) screen=unknown ;; *) screen=gone ;;
esac
echo "SCREEN=$screen"
echo "--- last screen lines (terminal $HANDLE)"
tail -n 30 "$screen_file" 2>/dev/null
[ "$screen" = gone ] && exit 3
exit 0
