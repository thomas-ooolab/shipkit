#!/usr/bin/env bash
# agent-usage.sh — measure a worker agent's REAL usage right now (never from memory, notes, a state file or an earlier run).
#   bash scripts/agent-usage.sh kiro|claude        # prints `MEASURED <agent> <UTC time>` then the agent's own usage lines
#   bash scripts/agent-usage.sh --self-test
# kiro:   `kiro-cli chat --no-interactive "/usage"` (plan credits used of the plan, reset date, overages) — local, no model turn.
# claude: `claude -p "/usage"` (current session % and week % with their reset times); only those lines are kept (the rest lists the user's sessions).
# Exit: 0 measured · 1 could not measure (the reason on stderr: the command's own output or "not installed") · 64 usage.
# KIRO_CLI / CLAUDE_CLI override the binaries (tests). Timeout: AGENT_USAGE_TIMEOUT seconds (default 60).
set -u
T="${AGENT_USAGE_TIMEOUT:-60}"
run() { if command -v timeout >/dev/null 2>&1; then timeout "$T" "$@"; else "$@"; fi; }

measure() {
  local agent="$1" out
  case "$agent" in
    kiro)   out=$(run "${KIRO_CLI:-kiro-cli}" chat --no-interactive "/usage" 2>&1) && echo "$out" | grep -qi "credits" || { echo "kiro usage not measured: ${out:-no output (not installed, or timed out after ${T}s)}" >&2; return 1; } ;;
    claude) out=$(run "${CLAUDE_CLI:-claude}" -p "/usage" 2>&1) && echo "$out" | grep -q "^Current session" || { echo "claude usage not measured: ${out:-no output (not installed, or timed out after ${T}s)}" >&2; return 1; }
            out=$(echo "$out" | grep -E "^(Current (session|week)|You are currently using)") ;;
    *) echo "usage: agent-usage.sh kiro|claude" >&2; return 64 ;;
  esac
  echo "MEASURED $agent $(date -u +%Y-%m-%dT%H:%MZ)"
  echo "$out"
}

if [ "${1:-}" = "--self-test" ]; then
  d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
  { echo '#!/bin/sh'; echo "cat <<'X'"; printf '%s\n' "Estimated Usage | resets on 2026-12-01 | KIRO POWER" "Credits (9233.16 of 10000 covered in plan), 92.3%" "Overages: Disabled" X; } > "$d/kiro"
  { echo '#!/bin/sh'; echo "cat <<'X'"; printf '%s\n' "You are currently using your subscription" "" "Current session: 54% used · resets 3:49pm" "Current week (all models): 8% used" "" "Last 24h · 1153 requests" "  83%  Start fresh" X; } > "$d/claude"
  printf '#!/bin/sh\necho "Error: not logged in"; exit 1\n' > "$d/broken"
  chmod +x "$d"/*
  o=$(KIRO_CLI="$d/kiro" bash "$0" kiro) && echo "$o" | grep -q "^MEASURED kiro " && echo "$o" | grep -q "9233.16 of 10000" || { echo "FAIL kiro: $o"; exit 1; }
  o=$(CLAUDE_CLI="$d/claude" bash "$0" claude) && echo "$o" | grep -q "^Current week" && ! echo "$o" | grep -q "Last 24h" || { echo "FAIL claude: $o"; exit 1; }
  KIRO_CLI="$d/broken" bash "$0" kiro >/dev/null 2>"$d/err"; [ $? = 1 ] && grep -q "not logged in" "$d/err" || { echo "FAIL broken"; exit 1; }
  KIRO_CLI="$d/none" bash "$0" kiro >/dev/null 2>&1; [ $? = 1 ] || { echo "FAIL missing binary"; exit 1; }
  bash "$0" gemini >/dev/null 2>&1; [ $? = 64 ] || { echo "FAIL usage"; exit 1; }
  echo "agent-usage self-test: ok"; exit 0
fi
measure "${1:-}"
