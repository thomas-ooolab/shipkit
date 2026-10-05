#!/usr/bin/env bash
# wait-for-slack-reply.sh — block until someone OTHER than me posts in a Slack thread, then exit.
# Run via Bash(run_in_background:true) to get ONE notification when there is real news instead of
# waking the whole session every tick.
#
#   usage: wait-for-slack-reply.sh <channel_id> <thread_ts> <after_ts> <my_user_id> [interval_s] [max_minutes]
#
# <thread_ts> is the thread ROOT. <after_ts> is the highest ts already handled (pass the ts of the
# reply you just posted, or the thread root on a fresh thread). Messages by <my_user_id> never count.
#
# exit 0  new message(s) from others — prints `NEW <count> latest_ts=<ts> author=<user>`; the CALLER
#         reads the thread (conversations.replies) and decides what, if anything, to answer.
# exit 2  timed out with nothing new — relaunch to keep waiting; not a failure.
# exit 3  $SLACK_REVIEW_TOKEN unset.
# exit 4  Slack rejected the call (bad token / scope / not in channel / thread not found).
# exit 6  <thread_ts> is a REPLY, not the root — Slack returns it as one message with ok:true, which
#         looks like "no replies yet" forever. Re-run with the root ts printed in the error.
#
# Needs groups:history (private) or channels:history (public) on the user token.
# SLACK_API_BASE exists only so the self-check can point at a local mock.

set -uo pipefail

CHANNEL="${1:?usage: wait-for-slack-reply.sh <channel_id> <thread_ts> <after_ts> <my_user_id> [interval_s] [max_minutes]}"
THREAD_TS="${2:?missing thread_ts}"
AFTER_TS="${3:?missing after_ts}"
ME="${4:?missing my_user_id}"
INTERVAL="${5:-15}"
MAX_MINUTES="${6:-60}"
API="${SLACK_API_BASE:-https://slack.com/api}"

if [ -z "${SLACK_REVIEW_TOKEN:-}" ]; then
  echo "NO_TOKEN: export SLACK_REVIEW_TOKEN (the user token that posts as you)." >&2
  exit 3
fi

deadline=$(( $(date +%s) + MAX_MINUTES * 60 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  # || true so one transient network failure never kills the wait.
  resp=$(curl -sS --max-time 20 -H "Authorization: Bearer ${SLACK_REVIEW_TOKEN}" \
    --data-urlencode "channel=${CHANNEL}" --data-urlencode "ts=${THREAD_TS}" \
    --data-urlencode "limit=200" -G "${API}/conversations.replies" 2>/dev/null) || true

  state=$(printf '%s' "$resp" | THREAD_TS="$THREAD_TS" AFTER_TS="$AFTER_TS" ME="$ME" python3 -c '
import json, os, sys
from decimal import Decimal
try:
    r = json.load(sys.stdin)
except Exception:
    print("retry"); sys.exit()
if not r.get("ok"):
    print("SLACK_ERROR|%s" % r.get("error", "unknown")); sys.exit()
msgs = r.get("messages", [])
if msgs and msgs[0].get("thread_ts", msgs[0]["ts"]) != msgs[0]["ts"]:
    print("NOT_ROOT|%s" % msgs[0]["thread_ts"]); sys.exit()
after = Decimal(os.environ["AFTER_TS"])
new = [m for m in msgs[1:] if Decimal(m["ts"]) > after and m.get("user") != os.environ["ME"]]
print("NEW %d latest_ts=%s author=%s" % (len(new), new[-1]["ts"], new[-1].get("user", "?")) if new else "waiting")
' 2>/dev/null) || true

  case "$state" in
    NEW*) echo "$state"; exit 0 ;;
    NOT_ROOT\|*)
      echo "WRONG_TS: ${THREAD_TS} is a reply, not the thread root. Re-run with root ts ${state#NOT_ROOT|}." >&2
      exit 6 ;;
    SLACK_ERROR\|*)
      echo "SLACK_ERROR: ${state#SLACK_ERROR|} (thread_not_found = wrong channel/ts; not_in_channel, missing_scope, invalid_auth = token/access)." >&2
      exit 4 ;;
  esac
  sleep "$INTERVAL"
done

echo "TIMEOUT after ${MAX_MINUTES}m: nothing new from anyone else." >&2
exit 2
