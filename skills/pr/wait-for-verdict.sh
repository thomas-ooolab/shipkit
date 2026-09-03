#!/usr/bin/env bash
# wait-for-verdict.sh — block until the OOOLAB AI Agent has replied in its review thread, then
# exit. Run via Bash(run_in_background:true) to get ONE notification the moment it says anything,
# instead of sleeping a fixed interval and guessing.
#
#   usage: wait-for-verdict.sh <parent_ts> [channel_id] [timeout_minutes] [after_ts]
#
# [after_ts] defaults to <parent_ts> — a no-op on a fresh thread. On a RE-TRIGGERED thread (round
# 2+: you just posted a new ask into a thread that already has an old answer sitting in it), pass
# the ts of your own trigger message here explicitly — otherwise the old answer from the PREVIOUS
# round reads as "changed" on the very first poll, before the bot has even seen the new request.
#
# exit 0  the agent replaced its "thinking…" placeholder — it said SOMETHING. Read the thread
#         and classify it: approval / findings / stall are all delivered this same way.
# exit 2  timed out with the bot still mid-flight
# exit 3  no token configured — CALLER MUST FALL BACK to the fixed-sleep poll
# exit 4  Slack rejected the request (bad token / not in channel) — configuration problem
# exit 5  config.json missing or missing required keys — never guesses a channel
# exit 6  <parent_ts> is a REPLY, not the thread ROOT — Slack does not error on this (it just
#         returns the single queried message, ok:true), so this is the only signal. Re-run with
#         the real root ts printed in the error (in pr, the state file's `thread_ts`).
#
# Requires a token in $SLACK_REVIEW_TOKEN.
#
# Channel, reviewer id and tunables are read from config.json — change them there, not here.
#
# ⚠️ The review channel is PRIVATE, so the scope is `groups:history` — NOT `channels:history`,
#    which only covers public channels. The bot must also be invited to the channel; a user
#    token (xoxp-) works if the human is already a member.
#
# The one thing this gets right: the agent posts ":thinking_face: thinking…" and then EDITS THAT
# SAME MESSAGE in place with its reply. So "a bot message exists" is true within ~2s and means
# nothing — the predicate must compare the TEXT against the placeholder. Every outcome (approval,
# findings, `msg_too_long`, a question back) shares that one transition, which is why this does
# not try to recognise verdict wording. See verdict-predicate.py for why that matters.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PARENT_TS="${1:?usage: wait-for-verdict.sh <parent_ts> [channel_id] [timeout_minutes] [after_ts]}"

# Addresses and tunables come from config.json — one edit to move channels. Args still win, so
# `wait-for-verdict.sh <ts> <channel> <mins>` overrides for a one-off. A missing or malformed
# config is a hard error, never a guessed default: silently watching the wrong channel would
# look exactly like a bot that never replied.
CONFIG="${HERE}/config.json"
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
# Defaults to PARENT_TS itself, which is a no-op filter on a fresh thread (every real bot reply
# has ts > the root). Pass this explicitly to the ts of your own trigger message on any ROUND 2+
# call — otherwise a long-lived thread's last (already-answered) bot message from a PRIOR round
# reads as an immediate "changed" before the bot has even seen the new request.
AFTER_TS="${4:-$PARENT_TS}"
last_wait=none

if [ -z "${SLACK_REVIEW_TOKEN:-}" ]; then
  echo "NO_TOKEN: \$SLACK_REVIEW_TOKEN unset — fall back to the fixed-sleep poll." >&2
  exit 3
fi

deadline=$(( $(date +%s) + TIMEOUT_MIN * 60 ))

while [ "$(date +%s)" -lt "$deadline" ]; do
  # || true so one transient network failure never kills the wait.
  resp=$(curl -sS --max-time 20 \
    -H "Authorization: Bearer ${SLACK_REVIEW_TOKEN}" \
    --data-urlencode "channel=${CHANNEL}" \
    --data-urlencode "ts=${PARENT_TS}" \
    --data-urlencode "limit=50" \
    -G "https://slack.com/api/conversations.replies" 2>/dev/null) || true

  state=$(printf '%s' "$resp" | BOT_ID="$BOT_ID" PARENT_TS="$PARENT_TS" AFTER_TS="$AFTER_TS" python3 "${HERE}/verdict-predicate.py" 2>/dev/null) || true

  case "$state" in
    waiting\|*)
      last_wait="${state#waiting|}"
      ;;
    NOT_ROOT\|*)
      real_root="${state#NOT_ROOT|}"
      echo "WRONG_TS: ${PARENT_TS} is a REPLY, not the thread root. Slack returned it as a" >&2
      echo "  single message (ok:true) instead of erroring, which looks identical to \"no" >&2
      echo "  replies yet\" — this waiter would have polled forever. Re-run with the real" >&2
      echo "  thread root: ${real_root} (in pr, this is the state file's \`thread_ts\`," >&2
      echo "  never the ts of whatever message you just posted)." >&2
      exit 6
      ;;
    SLACK_ERROR\|*)
      err="${state#SLACK_ERROR|}"
      # Different Slack errors have different fixes; one generic hint sent us looking at the
      # token when the real problem was a ts from a different channel.
      case "$err" in
        thread_not_found|message_not_found)
          echo "SLACK_ERROR: $err — no such thread in ${CHANNEL}. The parent ts is probably from a" >&2
          echo "  DIFFERENT channel (e.g. left over from before a channel migration), or the parent" >&2
          echo "  message was deleted. The token and channel access are fine." >&2
          ;;
        channel_not_found)
          echo "SLACK_ERROR: $err — ${CHANNEL} does not exist or the token cannot see it. Check" >&2
          echo "  slack.bot_review_channel.id in config.json." >&2
          ;;
        not_in_channel)
          echo "SLACK_ERROR: $err — the waiter bot is not a member of ${CHANNEL}. Run" >&2
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
    changed\|*)
      echo "AGENT REPLIED: ${state#changed|}"
      echo "(read the full thread and classify it yourself — a conditional \"LGTM after X\" is NOT an approval)"
      exit 0
      ;;
  esac

  sleep "$INTERVAL"
done

if [ "${last_wait:-none}" = "none" ]; then
  echo "TIMEOUT after ${TIMEOUT_MIN}m: the agent has posted NOTHING in this thread. It never picked" >&2
  echo "  up the request — check that the trigger contains <@${BOT_ID}> and was posted as a reply" >&2
  echo "  in this thread (a top-level post starts a separate, contextless review)." >&2
else
  echo "TIMEOUT after ${TIMEOUT_MIN}m: the agent is still showing only its \"thinking…\" placeholder." >&2
  echo "  The request landed; it is just slow. Nudge it per the skill's Stalls table." >&2
fi
exit 2
