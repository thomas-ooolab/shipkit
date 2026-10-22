#!/usr/bin/env bash
# Offline test of cleanup-browsers.sh with fake processes in temp directories (sleep stands in for node and chromium; nothing is launched).
# Note: the script also kills any real orphaned (PPID 1) ms-playwright chrome-headless-shell on the machine, as designed.
#   usage: bash scripts/test-cleanup-browsers.sh        exit 0 = all cases pass
set -u
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cleanup-browsers.sh"
A=$(mktemp -d); B=$(mktemp -d); AX="${A}x"; mkdir "$AX"          # A: the agent's scratch; B: somebody else's; AX: a sibling whose name starts with A's
pids=(); fail=0
trap 'kill -9 "${pids[@]}" 2>/dev/null; rm -rf "$A" "$B" "$AX"' EXIT
alive() { kill -0 "$1" 2>/dev/null; }
dead() { local i; for i in 1 2 3 4 5 6 7 8 9 10; do alive "$1" || return 0; sleep 0.3; done; return 1; }   # launchd reaps an orphan a moment later
check() { "$@" || { echo "FAIL  ${CASE:-?}"; fail=1; }; }
spawn_loop() { ( cd "$1" && exec bash -c 'while true; do sleep 1; done' ) & pids+=($!); LAST=$!; }

# the agent's chain: chain.sh -> tail.sh -> sleep, relaunching tail.sh whenever it exits
printf 'while true; do bash ./tail.sh; sleep 0.2; done\n' >"$A/chain.sh"; printf 'sleep 60\n' >"$A/tail.sh"
( cd "$A" && exec bash chain.sh ) & chain=$!; pids+=($chain)
# must survive: a loop in another directory, one in a sibling directory, a fake chromium with a live parent, the Playwright MCP's own browser
spawn_loop "$B"; other=$LAST; spawn_loop "$AX"; sibling=$LAST
mkdir -p "$B/ms-playwright/live" "$B/ms-playwright/orphan"
for k in live orphan; do printf '#!/usr/bin/env bash\necho $$ >"$0.pid"\nsleep 60 & wait\n' >"$B/ms-playwright/$k/chrome-headless-shell"; done
bash "$B/ms-playwright/live/chrome-headless-shell" & live=$!; pids+=($live)
( bash -c ': @playwright/mcp ms-playwright chrome-headless-shell; sleep 60 & wait' >/dev/null 2>&1 & )
# must die although outside the directory: an orphaned (PPID 1) headless shell of ms-playwright
( bash "$B/ms-playwright/orphan/chrome-headless-shell" >/dev/null 2>&1 & )
sleep 1; orphan=$(cat "$B/ms-playwright/orphan/chrome-headless-shell.pid" 2>/dev/null); [ -n "$orphan" ] && pids+=("$orphan")

CASE="the fixture is up"; check alive "$chain"; check alive "$other"; check alive "$sibling"; check test -n "$orphan"

CASE="--dry-run lists the chain and kills nothing"
out=$(bash "$SCRIPT" "$A" --dry-run); check grep -q "would kill $chain " <<<"$out"; check alive "$chain"; check alive "$orphan"

CASE="a bare run kills the chain and its children"
out=$(bash "$SCRIPT" "$A"); wait "$chain" 2>/dev/null
check grep -q "^kill $chain " <<<"$out"; check test "$(grep -c '^kill ' <<<"$out")" -ge 3; check dead "$chain"
CASE="the orphaned headless shell outside the directory is killed"; check dead "$orphan"

CASE="nothing relaunches after the run"; sleep 1; out=$(bash "$SCRIPT" "$A" --dry-run); check grep -q "nothing to clean" <<<"$out"

CASE="processes outside the directory survive"; check alive "$other"; check alive "$sibling"; check alive "$live"
CASE="the Playwright MCP lookalike survives"; check test -n "$(pgrep -f '@playwright/mcp ms-playwright')"; pkill -f '@playwright/mcp ms-playwright'

CASE="a missing directory is refused"; bash "$SCRIPT" "$A/nope" >/dev/null 2>&1; check test $? -eq 2
CASE="a broad directory is refused"; bash "$SCRIPT" "$HOME" >/dev/null 2>&1; check test $? -eq 2; bash "$SCRIPT" / >/dev/null 2>&1; check test $? -eq 2
CASE="no argument is refused"; bash "$SCRIPT" >/dev/null 2>&1; check test $? -eq 2
CASE="refusals killed nothing"; check alive "$other"; check alive "$sibling"

[ "$fail" -eq 0 ] && echo "cleanup-browsers: all cases pass"
exit "$fail"
