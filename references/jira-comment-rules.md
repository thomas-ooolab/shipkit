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

**REQUIRED:** before showing a draft for approval, Read `${CLAUDE_PLUGIN_ROOT}/references/humanize-text.md` and run the draft through
it (`humanizer:humanizer`); the text shown, approved and posted is the checked rewrite.

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

**Where the draft lives.** The draft is a file in the project's `.shipkit/`, next to the skill's state file: `.shipkit/<skill>-<ticket>-draft.md`
(`bugfix-AR-1-draft.md`, `clarify-AR-1-draft.md`). Never the session scratchpad, `/tmp` or the repo root: a new session or worktree must still
find it. `pending_comment` in the state file holds that relative path (or `null`), and the post is `jira-comment.py post <TICKET> --file <that
path>`. Images in the draft keep absolute paths into `.shipkit/evidence/<TICKET>/`. `/verify`'s evidence table
(`.shipkit/evidence/<TICKET>/jira-comment-*.md`) is a different file and stays where it is.

**No exceptions:** not for "just an acknowledgment" or "just a fixed-and-pushed note"; not because the wording is obviously
right; not because posting now and mentioning it in the summary afterward is faster. A drafted-but-unapproved comment is not
sent — and its item is not "resolved this tick" until it actually posts.

| Excuse | Reality |
|---|---|
| "It's just a routine ack, not worth asking about" | Every comment is public on the ticket — the user decides what goes out, not you. |
| "No one replied to the draft, but it's clearly right" | Silence isn't approval. No reply = no post, this tick. |
| "I'll post now and flag it in my summary" | Posting is the action that needs approval, not the summary after. |
| "Confirming breaks the autonomous loop" | It pauses posting, not the whole skill. Polling resumes normally once posted. |
| "A scratchpad / tmp file is quicker for the draft" | The next session or worktree can't find it and `pending_comment` points at nothing. The draft lives in `.shipkit/`. |

## Claims about today's behaviour and the scope of proposals — every draft, ours as well as the PO's words
A sentence in our draft that states as fact what the product, its data, the code or another ticket does or says now ("today X reads
Y", "right now trials keep 90 days", "the digest already skips…", "<KEY> says…") is a today-claim. A question, the other person's own
words, or a proposal that names no scope ("we'd build it so that…") is not (a proposal that does is covered by *Scope of a proposal* below). An option or proposal that presupposes something the system can already do — retry, redo, re-score, undo, notify, resend, schedule — is a today-claim about that ability, however it is phrased as a choice. Example: "B: the call is held back until the record is saved, and the save is retried automatically" claims a retry exists; its Claims line is `automatic retry of the save -> not found (<file>:<line> says nothing re-drives a failed save) | rewritten as a question: "should a failed save be retried? Today it is not"`. Before the draft is shown, every today-claim is one of:
- **backed** by a `file:line` read in the real code during this tick (not `specs/` or `docs/`), or by the quoted Jira comment with its
  id and link;
- **rewritten** as an open question ("which score does the call list show?");
- **dropped**.

"I assume", "probably" and "the spec says" are not backing. Code that could not be reached (no checkout, app not running) → rewrite
the claim as a question and mark it `unchecked: <reason>`. Same standard as `/developer`'s "answer only what is verified".

The backing never goes into the comment (Rule 1 forbids file names there). Show it next to the draft as a **Claims** list, one line per
today-claim: `<claim> -> <file:line> | <Jira link> | rewritten as a question | dropped | unchecked: <reason>`. A draft with a today-claim
and no Claims line is not shown for approval; a draft that is only questions has no Claims list. Build the list from the text that
came out of `humanize-text.md`, not from the draft before it.

**Scope of a proposal.** A proposal or option in our draft that names a scope ("every screen", "everywhere", "all reports", "only X") is
a scope-claim: it says how far the change reaches. Before the draft is shown, read the code for every consumer of the thing it changes —
the same sweep as `${CLAUDE_PLUGIN_ROOT}/skills/cross-check/SKILL.md` Step 3c ("every route that reads or acts on the entity": list,
detail, actions, jobs, exports, integrations) — and add a Claims line `<scope word> -> <n> consumers: <file:line>, …`. A consumer the
proposal does not cover, or that would behave differently under it, becomes its own question in the same comment (with its `OQ-N`), or
the proposal is narrowed to the places that were read ("the call list and the digest", not "every screen"). A consumer counts when it reads the same field or value, on the same record or on a related one (an older record type, an export, a job); never leave one out because it is not a screen or not the same record, ask about it. It is settled without
asking only when a quoted decision (Jira comment id and link) already settles it. Code that could not be reached → don't propose the
scope: ask which places should change, and mark the Claims line `unchecked: <reason>`. A proposal that names no scope needs no sweep.

## Numbering, and reading the comment back — for every comment posted with `jira-comment.py`
This part is for **any** skill's comment that carries a numbered list (the script is shared), not only `/clarify` and `/bugfix`. Jira
renumbers every list from 1 unless the list carries its start number, and a blank line or a heading ends a list. `jira-comment.py` writes
each block's first number (`attrs.order`), so a numbered list that a heading or a paragraph cuts apart counts on instead of restarting.
Number across topics by keeping the "N. " lines together in one block, or — `/clarify`'s and `/bugfix`'s own convention for their
questions, not for other skills — label each question with its `OQ-N` from `open-question.md` (`OQ-3. …`; one merged from several:
`OQ-3 / OQ-19. …`). The code is stable and never renumbered, so Jira, the spec and `open-question.md` all search alike, and "OQ-N." does
not match the script's `N. ` list pattern, so Jira never renumbers it. **After posting, read the comment back and check the numbers:** the id the script prints proves nothing about them.
`GET <JIRA_URL>/rest/api/3/issue/<TICKET>/comment/<id>` (credentials to curl on stdin, `curl -K -`, never on its command line), then
check every `orderedList` and its `attrs.order` in the body. A wrong number → `jira-comment.py edit <TICKET> <id> --file .shipkit/<skill>-<ticket>-draft.md`.
