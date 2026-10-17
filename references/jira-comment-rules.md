# Jira comment rules — shared by `/clarify` and `/bugfix`

Both skills post to a Jira ticket on the user's behalf inside a polling loop. These three rules are identical for both;
"item" below means a question (`/clarify`) or a concern (`/bugfix`).

## Rule 1 — business language only, both directions
Every comment — the first one AND any follow-up or acknowledgment once the other person answers — reads as plain business
language. No field/function/table names, endpoint paths, code, or ticket-internal jargon. Say what a non-technical reader
would say: what decision is needed (or what happens), in what situation, why, with what options. This holds even for a
comment that only confirms you understood.

Bad: "Confirming: `retention_days` defaults to 90 unless `plan_tier == enterprise`."
Good: "Got it — Enterprise workspaces keep call recordings for a year, everyone else for 90 days. Confirming that's right before I build it that way."

## Rule 2 — sound like a person, not a report
Write the way you'd type a quick reply: plain sentences, contractions, one thought running into the next. Not a bolded
outline, not a numbered list of items, no stock phrases ("please advise", "I hope this clarifies", "I've thoroughly
investigated…", "kindly confirm"). Several items in one comment still read as one person talking — run them together or
split with "also", not a heading per item.

Bad: "**Question 1:** Please confirm the retention period for Enterprise workspaces.\n**Question 2:** Please confirm whether the weekly digest should include workspaces with zero calls.\nKindly advise at your earliest convenience."
Good: "Two things I need from you — how long should Enterprise workspaces keep call recordings, a year or unlimited? And should the weekly digest still go out to workspaces that had zero calls that week, or skip them?"

## Rule 3 — confirm with the user before every Jira post
Never call the posting script until the user has explicitly approved the exact text. This covers the first comment and every
per-tick comment — status notes and acknowledgments included. (Fixing a real defect needs no approval — that is code, not a
public comment; only the comment describing it does.)

1. Draft the comment.
2. Show the exact text, verbatim — not a summary of what you plan to say.
3. Wait for explicit approval ("post it", "change X", "skip this one"). A wake with no reply yet means no post this tick —
   don't post because "no one objected" or "it's obviously fine, it's just an ack."
4. Only once approved: post it, then continue.

If the poller's notification arrives unattended (nobody has replied to the draft) → show the draft, write it into
`pending_comment` in the state file, and stop — don't relaunch the poller, since nothing new has been posted to poll replies
against. The next turn picks up from `pending_comment`, confirms it, and relaunches the poller only once it is posted.

**No exceptions:** not for "just an acknowledgment" or "just a fixed-and-pushed note"; not because the wording is obviously
right; not because posting now and mentioning it in the summary afterward is faster. A drafted-but-unapproved comment is not
sent — and its item is not "resolved this tick" until it actually posts.

| Excuse | Reality |
|---|---|
| "It's just a routine ack, not worth asking about" | Every comment is public on the ticket — the user decides what goes out, not you. |
| "No one replied to the draft, but it's clearly right" | Silence isn't approval. No reply = no post, this tick. |
| "I'll post now and flag it in my summary" | Posting is the action that needs approval, not the summary after. |
| "Confirming breaks the autonomous loop" | It pauses posting, not the whole skill. Polling resumes normally once posted. |
