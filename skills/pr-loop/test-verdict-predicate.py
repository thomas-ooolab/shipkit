#!/usr/bin/env python3
"""Tests for the review-loop waiter predicate. Run: python3 test-verdict-predicate.py

The property under test is narrow on purpose: has the agent written anything other than its
"thinking…" placeholder? Every real outcome — approval, findings, error — is reported the same
way (`changed`), because the caller must read the text regardless.
"""
import sys
from importlib.machinery import SourceFileLoader
p = SourceFileLoader("vp", "./verdict-predicate.py").load_module()
BOT = "U0B6M74TLBY"

def msgs(*texts):
    return {"ok": True, "messages": [{"user": BOT, "text": t} for t in texts]}

CASES = [
    # --- not finished: must keep waiting ---
    ("placeholder with emoji",            msgs(":thinking_face: thinking…"), "waiting"),
    ("placeholder with dots",             msgs("thinking..."), "waiting"),
    ("placeholder, odd spacing",          msgs("  :thinking_face:  thinking …  "), "waiting"),
    ("no bot message yet",                {"ok": True, "messages": []}, "waiting"),
    ("only the human request present",    {"ok": True, "messages": [{"user": "U0B54LPU9L5", "text": "review please"}]}, "waiting"),

    # --- finished: every outcome reports identically ---
    ("approval",                          msgs("LGTM :white_check_mark:"), "changed"),
    ("scoped approval",                   msgs("No blocking BE findings at 0395. LGTM ✅"), "changed"),
    ("blocking findings",                 msgs("- `login.go:77` — Blocking issue 🛑"), "changed"),
    ("needs changes",                     msgs("Verdict: Needs changes ⚠️"), "changed"),
    ("conditional LGTM",                  msgs("I'd mark this as LGTM after the doc line is fixed"), "changed"),
    ("msg_too_long stall",                msgs("⚠️ Something went wrong: 'msg_too_long'"), "changed"),
    ("no-response stall",                 msgs("Sorry — no response was produced."), "changed"),
    ("a question back to us",             msgs("Which sha should I review?"), "changed"),
    # The whole point of dropping the keyword list: unforeseen wording must still be detected.
    ("wording we never anticipated",      msgs("Ship it, nothing further from me."), "changed"),
    ("edit replaces placeholder",         msgs("thinking…", "LGTM ✅"), "changed"),

    # --- identity: must watch ONLY the configured agent (regression) ---
    # A message carrying a bot_id from a DIFFERENT app must not count as the reviewer replying.
    # The earlier `or m.get("bot_id")` clause accepted these and made BOT_ID meaningless.
    ("another app's message is ignored",  {"ok": True, "messages": [
        {"user": "U0OTHERBOT", "bot_id": "B0OTHER", "text": "Build #42 succeeded"}]}, "waiting"),
    ("human message is ignored",          {"ok": True, "messages": [
        {"user": "U0B54LPU9L5", "text": "<@U0B6M74TLBY> review these PRs"}]}, "waiting"),
    ("agent reply among other bots wins", {"ok": True, "messages": [
        {"user": "U0OTHERBOT", "bot_id": "B0OTHER", "text": "Build #42 succeeded"},
        {"user": BOT, "bot_id": "B0B6R49GA7K", "text": "LGTM ✅"}]}, "changed"),
    ("only other bots after the agent",   {"ok": True, "messages": [
        {"user": BOT, "bot_id": "B0B6R49GA7K", "text": ":thinking_face: thinking…"},
        {"user": "U0OTHERBOT", "bot_id": "B0OTHER", "text": "Deploy finished"}]}, "waiting"),

    # --- the two waiting states must be distinguishable for troubleshooting ---
    ("never started reports 'none'",      {"ok": True, "messages": []}, "waiting"),

    # --- transport ---
    ("slack rejection surfaces",          {"ok": False, "error": "not_in_channel"}, "SLACK_ERROR"),
]

fails = 0
for name, payload, expected in CASES:
    got = p.classify(payload, BOT)
    kind = got.split("|")[0] if got else None
    ok = kind == expected
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}: expected={expected} got={kind}")

# The predicate must never claim to know whether a message approves or rejects.
verdicty = p.classify(msgs("Verdict: Needs changes ⚠️"), BOT)
if verdicty and ("verdict" in verdicty.split("|")[0] or "approve" in verdicty.split("|")[0]):
    print("FAIL  predicate must not classify approve/reject"); fails += 1
else:
    print("PASS  predicate does not classify approve/reject")

# --- after_ts: a re-triggered thread must not report a PRIOR round's answer as new ---
# Reproduces the 2026-08-27 bug: a long-lived thread ends in a real (non-placeholder) bot
# message from round 1; a fresh human trigger is posted for round 2; the waiter must NOT see
# that stale round-1 message as "changed" before the bot has replied to the new trigger.
def msgs_ts(*pairs):
    return {"ok": True, "messages": [{"user": BOT, "ts": ts, "text": t} for ts, t in pairs]}

AFTER_CASES = [
    ("stale prior-round answer, no after_ts filter → false positive (documents the bug)",
     msgs_ts(("100", "LGTM :white_check_mark: (round 1)")), None, "changed"),
    ("stale prior-round answer, after_ts=trigger → correctly still waiting",
     msgs_ts(("100", "LGTM :white_check_mark: (round 1)")), "150", "waiting"),
    ("new placeholder after trigger → waiting (thinking)",
     msgs_ts(("100", "LGTM (round 1)"), ("200", ":thinking_face: thinking…")), "150", "waiting"),
    ("new real reply after trigger → changed, ignoring the stale one",
     msgs_ts(("100", "LGTM (round 1)"), ("200", "Needs changes ⚠️ (round 2)")), "150", "changed"),
]
for name, payload, after_ts, expected in AFTER_CASES:
    got = p.classify(payload, BOT, after_ts=after_ts)
    kind = got.split("|")[0] if got else None
    ok = kind == expected
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}: expected={expected} got={kind}")

total = len(CASES) + 1 + len(AFTER_CASES)
print(f"\n{total-fails}/{total} passed")
sys.exit(1 if fails else 0)
