#!/usr/bin/env python3
"""Decide whether the OOOLAB AI Agent has finished, for the review-loop waiter.

Reads a Slack `conversations.replies` payload on stdin and prints:

    changed|<text>     the agent's latest message is no longer the "thinking…" placeholder,
                       so it has produced SOMETHING — the caller reads it and decides what
    SLACK_ERROR|<err>  Slack rejected the call
    NOT_ROOT|<root_ts> the queried ts is itself a reply, not the thread root — Slack's API
                       silently returns just that one message (ok:true) instead of erroring,
                       so this is the only signal that the caller passed the wrong ts. Re-run
                       with <root_ts> (or, in this skill, the state file's `thread_ts`).
    waiting|none       the agent has posted nothing yet — keep waiting (if this persists, the
                       mention is probably missing or the trigger was not posted in-thread)
    waiting|thinking   only the "thinking…" placeholder so far — keep waiting

## Why this does not look for verdict keywords

The agent posts ":thinking_face: thinking…" and then EDITS THAT SAME MESSAGE in place with
whatever it produces — an approval, blocking findings, or an error like `msg_too_long`. So the
only state transition that matters is placeholder → not-placeholder. Every outcome shares it.

Earlier versions of this file instead matched a list of expected markers ("LGTM", "Blocking",
"msg_too_long", …). That was worse in both directions:

  * It could MISS. The list was a guess about future wording; any phrasing outside it left the
    waiter blocked forever — the precise failure the list existed to prevent.
  * It could LIE. While it still sorted matches into approve/reject, "Verdict: Needs changes"
    matched "verdict:" before "needs changes" and was reported as an approval. "no blocking"
    also contains "blocking", so no ordering fixes it.

Detecting "not the placeholder any more" cannot miss a variant, because it enumerates nothing.
Classification stays with the caller, who must read the message against the skill's verdict
table anyway — notably that a conditional "LGTM after X" is NOT an approval. That also covers
stalls: `msg_too_long` needs a nudge rather than triage, but the caller can only tell by
reading, so the waiter does not pretend to know.
"""

from __future__ import annotations

import json
import os
import re
import sys

# The placeholder is ":thinking_face: thinking…", but tolerate "thinking...", a bare emoji, or
# added whitespace. If stripping these leaves nothing, the agent has not written anything yet.
PLACEHOLDER_RE = re.compile(r"[:\w_]*thinking[:\w_]*|…|\.\.\.", re.I)


def classify(payload: dict, bot_id: str, parent_ts: str | None = None, after_ts: str | None = None) -> str | None:
    if not payload.get("ok"):
        return "SLACK_ERROR|%s" % payload.get("error", "unknown")

    # Guard against the caller passing a REPLY's ts instead of the thread ROOT's ts. Slack's
    # conversations.replies does not error on this — it just returns the single queried message
    # with ok:true, which looks identical to "a message with no replies yet" and would otherwise
    # have the waiter poll forever seeing nothing. A root message either has no "thread_ts" field
    # (no replies yet) or has "thread_ts" == its own ts; a reply's "thread_ts" points elsewhere.
    messages = payload.get("messages", [])
    if parent_ts and len(messages) == 1:
        only = messages[0]
        real_root = only.get("thread_ts")
        if only.get("ts") == parent_ts and real_root and real_root != parent_ts:
            return "NOT_ROOT|%s" % real_root

    # Guard against a STALE match in a long-lived, re-triggered thread. On round 2+ the thread
    # already ends in a real (non-placeholder) bot message from the PREVIOUS round — if we don't
    # exclude it, the very first poll after posting a new trigger sees that old answer and reports
    # "changed" immediately, before the bot has even started on the new request. after_ts is the
    # ts of the message that started this round (the human trigger); only bot messages strictly
    # after it count. Messages lacking a "ts" (unit tests) are kept — only real Slack payloads,
    # which always carry ts, are filtered.
    if after_ts:
        cutoff = float(after_ts)
        messages = [m for m in messages if "ts" not in m or float(m["ts"]) > cutoff]

    # Match ONLY the configured agent. An earlier version also accepted any message with a
    # `bot_id` set, which (a) made BOT_ID meaningless — the agent's own messages carry a bot_id,
    # so the filter passed them whatever id was configured — and (b) would treat ANY other app
    # posting in the thread as the reviewer answering, exiting early on an unrelated bot.
    texts = [
        m.get("text", "")
        for m in messages
        if m.get("user") == bot_id
    ]
    # The two not-done states are reported distinctly. This is NOT verdict classification —
    # it is why we are still waiting, and the two have different fixes: "never started" usually
    # means the mention is missing or the trigger was not posted in-thread, whereas "thinking"
    # means the request landed and it is simply slow.
    if not texts:
        return "waiting|none"  # hasn't picked up the request at all

    latest = texts[-1]
    if not PLACEHOLDER_RE.sub("", latest).strip():
        return "waiting|thinking"  # placeholder only

    return "changed|%s" % latest[:400].replace("\n", " ")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    result = classify(payload, os.environ.get("BOT_ID", "U0B6M74TLBY"), os.environ.get("PARENT_TS"), os.environ.get("AFTER_TS"))
    if result:
        print(result)


if __name__ == "__main__":
    main()
