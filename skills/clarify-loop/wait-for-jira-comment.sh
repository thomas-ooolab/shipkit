#!/usr/bin/env bash
# wait-for-jira-comment.sh — block in a background process until a NEW Jira comment lands on a
# ticket, then exit. Run via Bash(run_in_background:true) to get ONE notification the moment
# something posts, instead of a fixed-interval /loop (ScheduleWakeup) that pays for a full session
# wake (context reload) every tick just to find nothing changed.
#
#   usage: wait-for-jira-comment.sh <ticket> <after_comment_id> [interval_seconds] [max_minutes]
#
# <after_comment_id> is the highest comment id already seen (0 for "any comment at all" — e.g. a
# fresh ticket with none yet). Jira Cloud comment ids are monotonically increasing integers, so a
# plain numeric compare is enough to detect "new".
#
# exit 0  one or more new comments exist — print the count/latest id/author, then the CALLER reads
#         the ticket (via the Atlassian MCP tools, not this script) and classifies what was said.
#         This script only detects change; it never interprets content.
# exit 2  timed out after <max_minutes> with no new comment — relaunch the same command (bump
#         <after_comment_id> if it changed) to keep waiting; this is not a failure.
# exit 3  JIRA_URL / JIRA_EMAIL / JIRA_API_TOKEN not set — see the ecc `jira-integration` skill for
#         how to mint a token at https://id.atlassian.com/manage-profile/security/api-tokens. There
#         is no ScheduleWakeup fallback for this path anymore — these creds are required.
# exit 4  Jira rejected the request (bad auth / no access / wrong ticket key) — configuration
#         problem, not a stall.
#
# Requires JIRA_URL (e.g. https://yourorg.atlassian.net), JIRA_EMAIL, JIRA_API_TOKEN.

set -uo pipefail

TICKET="${1:?usage: wait-for-jira-comment.sh <ticket> <after_comment_id> [interval_seconds] [max_minutes]}"
AFTER_ID="${2:?usage: wait-for-jira-comment.sh <ticket> <after_comment_id> [interval_seconds] [max_minutes]}"
INTERVAL="${3:-60}"
MAX_MINUTES="${4:-1440}"

if [ -z "${JIRA_URL:-}" ] || [ -z "${JIRA_EMAIL:-}" ] || [ -z "${JIRA_API_TOKEN:-}" ]; then
  echo "NO_JIRA_CREDS: set JIRA_URL, JIRA_EMAIL and JIRA_API_TOKEN to use this poller." >&2
  echo "  See the ecc jira-integration skill — mint a token at" >&2
  echo "  https://id.atlassian.com/manage-profile/security/api-tokens" >&2
  exit 3
fi

deadline=$(( $(date +%s) + MAX_MINUTES * 60 ))

while [ "$(date +%s)" -lt "$deadline" ]; do
  # || true so one transient network failure never kills the wait.
  raw=$(curl -sS --max-time 20 -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
    -H "Accept: application/json" \
    "${JIRA_URL}/rest/api/3/issue/${TICKET}/comment?orderBy=created&maxResults=100" \
    -w '\n%{http_code}' 2>/dev/null) || true

  http_code=$(printf '%s' "$raw" | tail -n1)
  body=$(printf '%s' "$raw" | sed '$d')

  if [ "$http_code" != "200" ]; then
    echo "JIRA_ERROR: HTTP ${http_code:-?} from ${JIRA_URL}/rest/api/3/issue/${TICKET}/comment" >&2
    printf '%s\n' "$body" >&2
    exit 4
  fi

  result=$(printf '%s' "$body" | AFTER_ID="$AFTER_ID" python3 - <<'PY'
import json, os, sys
after = int(os.environ["AFTER_ID"])
try:
    data = json.load(sys.stdin)
except Exception as e:
    print(f"PARSE_ERROR|{e}")
    sys.exit()
comments = data.get("comments", [])
newer = sorted((c for c in comments if int(c["id"]) > after), key=lambda c: int(c["id"]))
if newer:
    latest = newer[-1]
    author = latest.get("author", {}).get("displayName", "?")
    print(f"NEW|{latest['id']}|{len(newer)}|{author}")
else:
    print("NONE|")
PY
) || true

  case "$result" in
    NEW\|*)
      IFS='|' read -r _ latest_id count author <<<"$result"
      echo "NEW_JIRA_COMMENT: ${count} new comment(s) on ${TICKET}, latest id=${latest_id} by ${author}"
      echo "(read the ticket yourself and classify what changed — this script only detects, never interprets)"
      exit 0
      ;;
    PARSE_ERROR\|*)
      echo "PARSE_ERROR (transient, retrying): ${result#PARSE_ERROR|}" >&2
      ;;
  esac

  sleep "$INTERVAL"
done

echo "TIMEOUT after ${MAX_MINUTES}m: no new comment on ${TICKET} since id ${AFTER_ID}." >&2
echo "  Relaunch the same command to keep waiting — this is expected for a quiet ticket." >&2
exit 2
