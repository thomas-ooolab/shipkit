#!/usr/bin/env bash
# wait-for-slack-reply.sh — block in a background process until a Slack thread has news, then exit.
# Run via Bash(run_in_background:true) to get ONE notification instead of waking the whole session
# every tick. One poll engine, two stop conditions (--until):
#
#   others   (default, /developer)  someone OTHER than me posted a NEW message in the thread.
#     usage: wait-for-slack-reply.sh [--until others] <channel_id> <thread_ts> <after_ts> <my_user_id> [interval_s] [max_minutes]
#     <after_ts> = highest ts already handled (the reply you just posted, or the root on a fresh
#     thread). Messages by <my_user_id> never count. Prints `NEW <count> latest_ts=<ts> author=<user>`.
#
#   verdict  (/pr review loop)      the OOOLAB AI Agent EDITED its "thinking…" placeholder into a
#     reply (same message, same ts — so "a new message" would never fire). Channel, bot id and
#     tunables come from skills/pr/config.json; the placeholder test lives in skills/pr/verdict-predicate.py.
#     usage: wait-for-slack-reply.sh --until verdict <parent_ts> [channel_id] [timeout_minutes] [after_ts]
#     Empty args ("") fall back to config. On a RE-TRIGGERED thread (round 2+) pass <after_ts> = the ts
#     of your own trigger message, else the previous round's answer reads as "changed" on poll one.
#     Prints `AGENT REPLIED: <text>`; the caller classifies it ("LGTM after X" is NOT an approval).
#
# <thread_ts>/<parent_ts> is the thread ROOT.
#
# exit 0  news — the CALLER reads the thread (conversations.replies) and decides what to do.
# exit 2  timed out with nothing — relaunch to keep waiting; not a failure (bad usage also exits 2).
# exit 3  $SLACK_REVIEW_TOKEN unset (verdict mode: caller falls back to a fixed-sleep poll).
# exit 4  Slack rejected the call (bad token / scope / not in channel / thread not found).
# exit 5  verdict mode: skills/pr/config.json missing or missing required keys — never guesses a channel.
# exit 6  <thread_ts> is a REPLY, not the root — Slack returns it as one message with ok:true, which
#         looks like "no replies yet" forever. Re-run with the root ts printed in the error.
#
# Needs groups:history (private channel) — NOT channels:history, which covers public only — or
# channels:history (public) on the user token. SLACK_API_BASE exists only to point at a local mock.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PR_DIR="${HERE}/../skills/pr"
API="${SLACK_API_BASE:-https://slack.com/api}"

MODE=others
if [ "${1:-}" = "--until" ]; then
  MODE="${2:-}"
  if [ $# -ge 2 ]; then shift 2; else shift; fi
fi

case "$MODE" in
  others)
    CHANNEL="${1:?usage: wait-for-slack-reply.sh [--until others] <channel_id> <thread_ts> <after_ts> <my_user_id> [interval_s] [max_minutes]}"
    THREAD_TS="${2:?missing thread_ts}"
    AFTER_TS="${3:?missing after_ts}"
    ME="${4:?missing my_user_id}"
    INTERVAL="${5:-15}"
    TIMEOUT_MIN="${6:-60}"
    LIMIT=200
    ;;
  verdict)
    THREAD_TS="${1:?usage: wait-for-slack-reply.sh --until verdict <parent_ts> [channel_id] [timeout_minutes] [after_ts]}"
    # Addresses and tunables come from config.json — one edit to move channels. Args still win. A
    # missing or malformed config is a hard error, never a guessed default: silently watching the
    # wrong channel would look exactly like a bot that never replied.
    CONFIG="${PR_DIR}/config.json"
    if [ ! -f "$CONFIG" ]; then
      echo "CONFIG_MISSING: $CONFIG not found — cannot resolve the review channel." >&2
      exit 5
    fi
    cfg=$(python3 - "$CONFIG" <<'PYCFG'
import json, sys
try:
    c = json.load(open(sys.argv[1]))
    s, w = c["slack"], c["waiter"]
    print(s["bot_review_channel"]["id"])
    print(s["bot_reviewer_user_id"])
    print(w["poll_interval_seconds"])
    print(w["default_timeout_minutes"])
except Exception as e:
    print("ERR:%s" % e)
PYCFG
    ) || true
    case "$cfg" in
      ERR:*|"")
        echo "CONFIG_INVALID: could not read required keys from $CONFIG (${cfg#ERR:})." >&2
        echo "  Needs slack.bot_review_channel.id, slack.bot_reviewer_user_id," >&2
        echo "  waiter.poll_interval_seconds, waiter.default_timeout_minutes." >&2
        exit 5
        ;;
    esac
    CHANNEL="${2:-$(printf '%s\n' "$cfg" | sed -n 1p)}"
    BOT_ID="${BOT_ID:-$(printf '%s\n' "$cfg" | sed -n 2p)}"
    INTERVAL=$(printf '%s\n' "$cfg" | sed -n 3p)
    TIMEOUT_MIN="${3:-$(printf '%s\n' "$cfg" | sed -n 4p)}"
    # Defaults to THREAD_TS: a no-op filter on a fresh thread (every real bot reply has ts > the root).
    AFTER_TS="${4:-$THREAD_TS}"
    LIMIT=50
    last_wait=none
    ;;
  *)
    echo "usage: wait-for-slack-reply.sh [--until others|verdict] ... (see the header of this script)" >&2
    exit 2
    ;;
esac

if [ -z "${SLACK_REVIEW_TOKEN:-}" ]; then
  if [ "$MODE" = verdict ]; then
    echo "NO_TOKEN: \$SLACK_REVIEW_TOKEN unset — fall back to the fixed-sleep poll." >&2
  else
    echo "NO_TOKEN: export SLACK_REVIEW_TOKEN (the user token that posts as you)." >&2
  fi
  exit 3
fi

deadline=$(( $(date +%s) + TIMEOUT_MIN * 60 ))

while [ "$(date +%s)" -lt "$deadline" ]; do
  # || true so one transient network failure never kills the wait.
  resp=$(curl -sS --max-time 20 -H "Authorization: Bearer ${SLACK_REVIEW_TOKEN}" \
    --data-urlencode "channel=${CHANNEL}" --data-urlencode "ts=${THREAD_TS}" \
    --data-urlencode "limit=${LIMIT}" -G "${API}/conversations.replies" 2>/dev/null) || true

  if [ "$MODE" = verdict ]; then
    state=$(printf '%s' "$resp" | BOT_ID="$BOT_ID" PARENT_TS="$THREAD_TS" AFTER_TS="$AFTER_TS" python3 "${PR_DIR}/verdict-predicate.py" 2>/dev/null) || true
  else
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
  fi

  case "$state" in
    NEW\ *) echo "$state"; exit 0 ;;
    changed\|*)
      echo "AGENT REPLIED: ${state#changed|}"
      echo "(read the full thread and classify it yourself — a conditional \"LGTM after X\" is NOT an approval)"
      exit 0
      ;;
    waiting\|*) last_wait="${state#waiting|}" ;;
    NOT_ROOT\|*)
      echo "WRONG_TS: ${THREAD_TS} is a REPLY, not the thread root. Slack returned it as a" >&2
      echo "  single message (ok:true) instead of erroring, which looks identical to \"no" >&2
      echo "  replies yet\" — this waiter would have polled forever. Re-run with the real" >&2
      echo "  thread root: ${state#NOT_ROOT|} (in pr, this is the state file's \`thread_ts\`," >&2
      echo "  never the ts of whatever message you just posted)." >&2
      exit 6
      ;;
    SLACK_ERROR\|*)
      err="${state#SLACK_ERROR|}"
      # Different Slack errors have different fixes; one generic hint sent us looking at the
      # token when the real problem was a ts from a different channel.
      case "$err" in
        thread_not_found|message_not_found)
          echo "SLACK_ERROR: $err — no such thread in ${CHANNEL}. The thread ts is probably from a" >&2
          echo "  DIFFERENT channel (e.g. left over from before a channel migration), or the parent" >&2
          echo "  message was deleted. The token and channel access are fine." >&2
          ;;
        channel_not_found)
          echo "SLACK_ERROR: $err — ${CHANNEL} does not exist or the token cannot see it. Check the" >&2
          echo "  channel id (verdict mode: slack.bot_review_channel.id in skills/pr/config.json)." >&2
          ;;
        not_in_channel)
          echo "SLACK_ERROR: $err — the token's identity is not a member of ${CHANNEL}. Run" >&2
          echo "  /invite for it in that channel." >&2
          ;;
        missing_scope)
          echo "SLACK_ERROR: $err — token lacks groups:history (a PRIVATE channel needs it;" >&2
          echo "  channels:history covers public only). Re-check the app's scopes." >&2
          ;;
        invalid_auth|token_revoked|account_inactive)
          echo "SLACK_ERROR: $err — the token is bad or revoked. Check \$SLACK_REVIEW_TOKEN." >&2
          ;;
        *)
          echo "SLACK_ERROR: $err — unexpected. Check the token, its scopes, and that its identity" >&2
          echo "  is in ${CHANNEL}." >&2
          ;;
      esac
      exit 4
      ;;
  esac
  sleep "$INTERVAL"
done

if [ "$MODE" = others ]; then
  echo "TIMEOUT after ${TIMEOUT_MIN}m: nothing new from anyone else." >&2
elif [ "${last_wait:-none}" = "none" ]; then
  echo "TIMEOUT after ${TIMEOUT_MIN}m: the agent has posted NOTHING in this thread. It never picked" >&2
  echo "  up the request — check that the trigger contains <@${BOT_ID}> and was posted as a reply" >&2
  echo "  in this thread (a top-level post starts a separate, contextless review)." >&2
else
  echo "TIMEOUT after ${TIMEOUT_MIN}m: the agent is still showing only its \"thinking…\" placeholder." >&2
  echo "  The request landed; it is just slow. Nudge it per the skill's Stalls table." >&2
fi
exit 2
