#!/usr/bin/env bash
# send-when-ready.sh <terminal-handle> "<text>" [timeout-seconds] — wait until the coding agent in an Orca terminal is
# at an empty input box, send ONE message, and confirm the agent started working on it. One script for the whole
# "Ready check + Send" so no session hand-writes its own loop (a hand-written `head -1 | grep "^agent"` against
# `wait-for-agent.sh` never matched its first line `SCREEN=agent`, looped, exited 0 and typed nothing: AR-683/680/674).
#
#   usage: send-when-ready.sh <terminal-handle> "<text>" [timeout-seconds, default 240]
#          send-when-ready.sh --self-test
#
# Steps: `terminal wait --for tui-idle` (a first hint only), then `wait-for-agent.sh --once` every few seconds until
# SCREEN=agent AND the input box holds no typed text; `terminal send --text … --enter --wait-submit 10` (never resent);
# then `wait-for-agent.sh --once` until SCREEN=working. `tui-idle` alone is never the judge: a bare shell is idle too.
#
# stdout: first line RESULT=<name>, then why, then the last screen lines. stderr: nothing the caller needs.
# Exit codes — a non-zero exit means NOTHING was confirmed; the caller reports it and never says "sent":
#   0   sent       the message was sent and the agent is working on it (RESULT=sent)
#   10  not-ready  no empty agent input box within the timeout (shell prompt, still drawing, text already in the box,
#                  or the agent busy the whole time); nothing was sent
#   11  attention  the agent is stopped on a y/n or numbered prompt — a person answers it (before or after the send)
#   12  login      "Not logged in" / unavailable screen; nothing was sent
#   13  limit      the agent's quota notice is on screen
#   14  gone       the terminal is closed or Orca is unreachable
#   15  never-started  the message was sent but the agent never started working (or the text landed in a shell)
#   16  send-failed  `terminal send` itself was refused or errored; nothing was sent
#   64  bad usage
# attention / login / limit / gone must be seen on two reads in a row, so a screen that is mid-redraw is not mistaken.
# Env: ORCA_CLI_COMMAND (as wait-for-agent.sh), SEND_WHEN_READY_POLL (seconds between reads, default 3),
#      SEND_WHEN_READY_START (seconds to wait for the agent to start working after the send, default 30).

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USAGE='usage: send-when-ready.sh <terminal-handle> "<text>" [timeout-seconds]'

if [ "${1:-}" = "--self-test" ]; then
  pass=0; fail=0; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  # A stub `orca`: `terminal read` prints $STUB/screen.json, `terminal send` logs its arguments and swaps in
  # $STUB/after.json (when it exists), `terminal wait` succeeds (or times out when $STUB/wait-timeout exists).
  cat >"$tmp/orca" <<'STUB'
#!/usr/bin/env bash
case "$2" in
  read) cat "$STUB/screen.json" ;;
  wait) if [ -e "$STUB/wait-timeout" ]; then echo '{"ok":false,"error":{"code":"timeout"}}'; else echo '{"ok":true,"result":{"wait":{"satisfied":true}}}'; fi ;;
  send) [ -e "$STUB/send-fails" ] && { echo '{"ok":false,"error":{"code":"nope"}}'; exit 1; }
        echo "$*" >>"$STUB/send.log"
        [ -e "$STUB/after.json" ] && cp "$STUB/after.json" "$STUB/screen.json"
        echo '{"ok":true,"result":{"send":{"accepted":true,"prompt":{"stages":["input_accepted"]}}}}' ;;
esac
STUB
  chmod +x "$tmp/orca"
  rule='────────────────────────────────'
  screen() { python3 -I -c 'import json,sys; print(json.dumps({"ok": True, "result": {"terminal": {"status": "running", "tail": sys.argv[1:]}}}))' "$@"; }
  gone()   { echo '{"ok":false,"error":{"code":"terminal_not_found"}}'; }
  # check <name> <expected exit> <expected RESULT> <was the message sent: yes|no> — reads $tmp/s/{screen,after}.json
  check() {
    local name="$1" want="$2" res="$3" sent="$4" out rc
    out=$(STUB="$tmp/s" ORCA_CLI_COMMAND="$tmp/orca" SEND_WHEN_READY_POLL=0.1 SEND_WHEN_READY_START=1 \
          bash "$HERE/send-when-ready.sh" h "/run-pipeline AR-1 auto" 2 2>&1); rc=$?
    local got_sent=no; grep -q -- '--enter --wait-submit 10' "$tmp/s/send.log" 2>/dev/null && grep -q 'run-pipeline AR-1 auto' "$tmp/s/send.log" && got_sent=yes
    if [ "$rc" = "$want" ] && [ "$(echo "$out" | head -1)" = "RESULT=$res" ] && [ "$got_sent" = "$sent" ]; then pass=$((pass+1)); echo "ok    send-when-ready: $name"
    else fail=$((fail+1)); echo "FAIL  send-when-ready: $name (exit $rc want $want, first line '$(echo "$out" | head -1)', sent $got_sent want $sent)"; echo "$out" | sed 's/^/        /' | head -8; fi
  }
  fresh() { rm -rf "$tmp/s"; mkdir "$tmp/s"; }
  idle=$(screen "some banner" "$rule" "❯ " "$rule" "  ⏵⏵ bypass permissions on (shift+tab to cycle)")
  kidle=$(screen "• Write file:///x" "▸ What's new" "$rule" "Default · gpt-5.6-sol · medium · ◔ 1%        ~/x · (main)" "›  ask a question or describe a task ↵")
  ktyped=$(screen "$rule" "old tool output" "$rule" "• ok" "$rule" "Default · gpt-5.6-sol · medium · ◔ 1%        ~/x · (main)" "› half typed by the user")
  kold=$(screen "• tool" "$rule" "  Reply with the single word: ok" "$rule" "• ok" "$rule" "Default · gpt-5.6-sol · medium · ◔ 1%        ~/x · (main)" "›  ask a question or describe a task ↵")
  kbusy=$(screen "Thinking..." "$rule" "Default · gpt-5.6-sol · medium · ◔ 1%        ~/x · (main)" "›  type to queue a message")
  busy=$(screen "✢ Frosting… (1m 19s · esc to interrupt)" "$rule" "❯ " "$rule")
  fresh; echo "$idle" >"$tmp/s/screen.json"; echo "$busy" >"$tmp/s/after.json"
  check "idle box, send, agent starts working -> sent" 0 sent yes
  fresh; echo "$idle" >"$tmp/s/screen.json"; touch "$tmp/s/wait-timeout"; echo "$busy" >"$tmp/s/after.json"
  check "tui-idle wait timing out does not decide" 0 sent yes
  fresh; echo "$idle" >"$tmp/s/screen.json"
  check "sent but the agent never works -> never-started" 15 never-started yes
  fresh; screen "user@host ~ % " >"$tmp/s/screen.json"
  check "shell prompt the whole time -> not-ready, nothing sent" 10 not-ready no
  fresh; screen "banner" "$rule" "❯ half typed by the user" "$rule" >"$tmp/s/screen.json"
  check "text already in the input box -> not-ready, nothing sent" 10 not-ready no
  fresh; echo "$kidle" >"$tmp/s/screen.json"; echo "$kbusy" >"$tmp/s/after.json"
  check "kiro V3 idle box (one rule, placeholder) -> sent" 0 sent yes
  fresh; echo "$kold" >"$tmp/s/screen.json"; echo "$kbusy" >"$tmp/s/after.json"
  check "kiro V3: earlier conversation above an empty box is not typed text -> sent" 0 sent yes
  fresh; echo "$ktyped" >"$tmp/s/screen.json"
  check "kiro V3: text typed in the box -> not-ready, nothing sent" 10 not-ready no
  fresh; screen "banner" "$rule" "❯ Try \"fix a bug\"" "$rule" >"$tmp/s/screen.json"; echo "$busy" >"$tmp/s/after.json"
  check "placeholder in the box is empty -> sent" 0 sent yes
  fresh; screen "Allow this edit? (y/n)" >"$tmp/s/screen.json"
  check "permission prompt -> attention, nothing sent" 11 attention no
  fresh; screen "Not logged in · Run /login" >"$tmp/s/screen.json"
  check "login screen -> login, nothing sent" 12 login no
  fresh; screen "• You've reached your monthly usage limit. Please return next month to continue building." "$rule" "x" "$rule" >"$tmp/s/screen.json"
  check "quota notice -> limit, nothing sent" 13 limit no
  fresh; gone >"$tmp/s/screen.json"
  check "closed terminal -> gone, nothing sent" 14 gone no
  fresh; echo "$idle" >"$tmp/s/screen.json"; touch "$tmp/s/send-fails"
  check "terminal send refused -> send-failed" 16 send-failed no
  fresh; echo "$idle" >"$tmp/s/screen.json"; screen "Allow this edit? (y/n)" >"$tmp/s/after.json"
  check "prompt right after the send -> attention" 11 attention yes
  fresh; echo "$idle" >"$tmp/s/screen.json"; screen "user@host ~ % /run-pipeline AR-1 auto" >"$tmp/s/after.json"
  check "text landed in a shell -> never-started" 15 never-started yes
  bash "$HERE/send-when-ready.sh" >/dev/null 2>&1; [ $? -eq 64 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL  send-when-ready: no arguments -> 64"; }
  bash "$HERE/send-when-ready.sh" h "" >/dev/null 2>&1; [ $? -eq 64 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL  send-when-ready: empty text -> 64"; }
  echo "send-when-ready.sh self-test: $pass passed, $fail failed"; [ "$fail" = 0 ]; exit $?
fi

HANDLE="${1:-}"; TEXT="${2:-}"; TIMEOUT="${3:-240}"
[ -n "$HANDLE" ] && [ -n "$TEXT" ] && [ "$#" -le 3 ] && [[ "$TIMEOUT" =~ ^[0-9]+$ ]] || { echo "$USAGE" >&2; exit 64; }
POLL="${SEND_WHEN_READY_POLL:-3}"; START="${SEND_WHEN_READY_START:-30}"

if [ -n "${ORCA_CLI_COMMAND:-}" ]; then ORCA="$ORCA_CLI_COMMAND"
elif [ -n "${ORCA_DEV_REPO_ROOT:-}" ]; then ORCA="orca-dev"
elif [ "$(uname -s)" = "Linux" ]; then ORCA="orca-ide"
else ORCA="orca"; fi

now() { date +%s; }
last_screen=""
# look: one read of the terminal -> LOOK_SCREEN (the SCREEN= value) and LOOK_TAIL (the lines after it)
look() {
  last_screen=$(bash "$HERE/wait-for-agent.sh" "$HANDLE" --once 2>/dev/null)
  LOOK_SCREEN=$(printf '%s\n' "$last_screen" | sed -n 's/^SCREEN=//p;' | head -1)
  LOOK_TAIL=$(printf '%s\n' "$last_screen" | sed '1d')
  [ -n "$LOOK_SCREEN" ] || LOOK_SCREEN=gone
}
finish() { # <exit> <RESULT> <why>
  echo "RESULT=$2"; echo "$3"; printf '%s\n' "$LOOK_TAIL" | tail -n 32; exit "$1"
}
# box_text: the typed text of the agent's input box, "" when it is empty or only a placeholder. Two layouts, both seen on real screens:
#   kiro V3: one rule, a status line, then the input as the LAST line, `› <text>` (placeholder `› ask a question or describe a task ↵`);
#   claude:  the input between the last two rules, `❯ <text>`, the rules within the last few lines (status lines under the bottom rule).
# Anything else (no box found) reads as empty. Older conversation lines above the box are never looked at.
box_text() {
  printf '%s\n' "$LOOK_TAIL" | python3 -I -c '
import re, sys
lines = [l for l in sys.stdin.read().splitlines() if l.strip()]
rule = re.compile(r"[─━]{8,}")
chrome = re.compile(r"Trust All Tools|/quit|⏵|bypass permissions|shift\+tab|\? for shortcuts|ask a question|type to queue|Try \"|^Default ·|Credits:|esc to|↵\s*$")
def clean(l): return re.sub(r"^[\s│┃>❯›]+", "", l).rstrip(" │┃")
def typed(ls):
    for l in ls:
        t = clean(l)
        if t.strip() and not chrome.search(t): return t.strip()
    return ""
if lines and re.match(r"^\s*[›❯>]", lines[-1]) and any(rule.search(l) for l in lines[-4:-1]):
    print(typed(lines[-1:])); sys.exit()
rules = [i for i, l in enumerate(lines) if rule.search(l)]
for a, b in reversed(list(zip(rules, rules[1:]))):
    if 1 <= b - a <= 6 and b >= len(lines) - 6:
        print(typed(lines[a + 1 : b])); break
'
}

# 1. a first hint, then judge by reading the screen (tui-idle never decides)
left=$(( TIMEOUT )); [ "$left" -gt 60 ] && left=60
"$ORCA" terminal wait --terminal "$HANDLE" --for tui-idle --timeout-ms $(( left * 1000 )) --json >/dev/null 2>&1 || true

deadline=$(( $(now) + TIMEOUT )); prev=""; streak=0; typed=""
while :; do
  look
  case "$LOOK_SCREEN" in
    attention|login|limit|gone)
      if [ "$prev" = "$LOOK_SCREEN" ]; then streak=$((streak+1)); else streak=1; fi
      if [ "$streak" -ge 2 ]; then
        case "$LOOK_SCREEN" in
          attention) finish 11 attention "the agent is stopped on a prompt — a person answers it; nothing was sent" ;;
          login)     finish 12 login "the agent is not logged in; nothing was sent" ;;
          limit)     finish 13 limit "the agent's quota notice is on screen; nothing was sent" ;;
          gone)      finish 14 gone "the terminal is closed or Orca is unreachable; nothing was sent" ;;
        esac
      fi ;;
    agent)
      streak=0; typed=$(box_text)
      [ -z "$typed" ] && break ;;
    *) streak=0 ;;
  esac
  prev="$LOOK_SCREEN"
  [ "$(now)" -ge "$deadline" ] && break
  sleep "$POLL"
done
if [ "$LOOK_SCREEN" != agent ] || [ -n "$typed" ]; then
  why="no empty agent input box within ${TIMEOUT}s (last SCREEN=$LOOK_SCREEN)"; [ -n "$typed" ] && why="$why; the box already holds text: $typed"
  finish 10 not-ready "$why; nothing was sent"
fi

# 2. send once, never resend (a receipt that only says input_accepted is unconfirmed)
resp=$("$ORCA" terminal send --terminal "$HANDLE" --text "$TEXT" --enter --wait-submit 10 --json 2>/dev/null) || resp=""
ok=$(printf '%s' "$resp" | python3 -I -c 'import json,sys
try: d = json.load(sys.stdin); print("yes" if d.get("ok") and (d.get("result") or {}).get("send", {}).get("accepted") else "no")
except Exception: print("no")')
[ "$ok" = yes ] || finish 16 send-failed "terminal send was refused or errored; nothing was sent"

# 3. confirm the agent started working on it
deadline=$(( $(now) + START ))
while :; do
  look
  case "$LOOK_SCREEN" in
    working)   finish 0 sent "sent to $HANDLE; the agent is working" ;;
    attention) finish 11 attention "the agent stopped on a prompt after the message was sent" ;;
    limit)     finish 13 limit "the agent's quota notice appeared after the message was sent" ;;
    login)     finish 12 login "the agent is not logged in; the message was sent but not worked on" ;;
    shell)     finish 15 never-started "the screen shows a shell prompt: the text probably landed in a shell, not an agent" ;;
  esac
  [ "$(now)" -ge "$deadline" ] && break
  sleep "$POLL"
done
finish 15 never-started "the message was sent but the agent did not start working within ${START}s (last SCREEN=$LOOK_SCREEN)"
