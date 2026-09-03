---
name: pr-loop
description: "Use when submodule PRs for a ticket have just been opened (typically right after /pre-pr) and need an automated reviewer's sign-off — pings the reviewer in Slack with the PR links, then polls their thread replies, verifying each raised concern against the real code and the live Jira ticket before deciding whether to fix it outright, escalate it to Jira for a product decision, or explain why it isn't an issue — looping until every concern the reviewer raised is resolved, not just replied to once. Trigger: /pr-loop <ticket-id>. Examples: \"/pr-loop AR-450\", \"pr-loop AR-458 after pre-pr\", \"ping the reviewer and keep triaging until AR-450's PRs are clean\""
---

# PR Loop

Ping the designated reviewer, triage each concern they raise against the real code and the real Jira ticket (never take a review comment at face value — debate it), fix what's actually broken, escalate what needs a product call, explain what isn't a bug — then keep checking the thread until every concern is resolved.

Fixed reviewer for this skill: Slack user `U0B6M74TLBY` ("OOOLAB AI Agent"), channel `#ent-internal` (`C052QGHD337`).

Composes existing pieces — do not reimplement any of them:
- **REQUIRED:** `superpowers:systematic-debugging` — trace each raised concern to the real code path before classifying it. Never classify from the reviewer's wording alone.
- **REQUIRED for any code fix:** `superpowers:test-driven-development` — write the regression test first.
- **REQUIRED:** this project's `review-pr` skill — reuse its PR-discovery queries (Step 1: find open PRs for the ticket's branches across submodules) and its fix/commit/push/quality-check mechanics (Steps 3–5: minimal fix, preserve `REQ-SDD-NNN` citations, run the right submodule's checks, commit, push). Don't re-derive any of that here.
- `bugfix-loop`'s state-file/`silent_ticks` shape, applied to a Slack thread instead of a Jira comment thread — but **not** its `ScheduleWakeup` backoff. Like `clarify-loop`, this skill polls via background bash scripts instead of `/loop`'s `ScheduleWakeup`, which reloads the whole session's context on every tick even when nothing changed.
- **REQUIRED:** this skill's own `wait-for-verdict.sh` + `verdict-predicate.py` (colocated in this folder, copied 2026-08-20 from `/Users/tung/ooolab/review-loop` — battle-tested there against this exact reviewer bot, `U0B6M74TLBY`). Use it verbatim for "has the reviewer replied yet?" instead of blind fixed-interval polling — see Step 3 below. It reads its channel/bot id/tunables from this folder's own `config.json` (already pointed at `#ent-internal` / `C052QGHD337`) — don't hardcode those values elsewhere, and don't confuse this file with review-loop's separate `config.json`, which targets a different channel (`#ooolab-be`) for a different pipeline.
- **REQUIRED for the Jira PO-decision check:** `wait-for-jira-comment.sh` (colocated in this folder as a symlink to `clarify-loop`'s copy — one script, one source of truth). No `ScheduleWakeup` anywhere in this skill, and no fallback when a token is missing: `SLACK_REVIEW_TOKEN` and `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` are hard requirements now, same as they are for `clarify-loop`.

State lives in `.shipkit/pr-loop-<ticket>.md`.

## Hard rule: debate every concern, don't just accept it

A review comment is a claim, not a fact. Before classifying anything, read the actual diff for the file/line in question and pull the live Jira ticket (`getJiraIssue` — description, comments, linked tickets; not just the local `spec.md`, which can drift). Weigh the reviewer's claim against what the code and the ticket actually say. Three outcomes only, and the ticket/code decide which:

- **Real defect, no product call needed** — the code contradicts the ticket's own stated requirement, or its own stated intent, plainly and without ambiguity → fix it.
- **Real issue, needs a product decision** — could be intentional or wrong depending on unstated business intent, or more than one valid fix exists → escalate to Jira, don't fix yet.
- **Not an issue** — the code does exactly what the ticket asked for, or the reviewer's claim doesn't hold up against the real implementation → say so, with the reasoning, not just "not a bug."

A concern that's actually correct doesn't become "needs a decision" just because it's easier to punt. A concern that's genuinely ambiguous doesn't become "not an issue" just because you'd rather not open a Jira thread. Classify on what you find, not on what's convenient.

## Hard rule: Slack posts directly, Jira posts need my confirmation first

These are not symmetric. A Slack thread reply is fast-moving, cheap to follow up on, and read only by the reviewer and whoever's in `#ent-internal`; a Jira comment is a durable, org-visible record on the ticket itself, and the one that pulls the PO in to make a call. Slack messages post without waiting on me. Jira comments still do.

**Slack: draft it, tag correctly, post it — no approval wait.** Fixing a real defect never needed approval (that's code); now the message describing it, the tick-reply summary, the not-an-issue explanation, and the sign-off ack don't either. Still apply the tagging rule below and the debate/classification discipline elsewhere in this skill — "no approval needed" is not "skip the thinking," it's "don't pause for a yes before sending."

**Jira: still draft → show me → wait for explicit approval → post.** A wake with no reply yet means no post this tick.

1. Draft the comment.
2. Show me the exact text, verbatim.
3. Wait for explicit approval ("post it", "change X", "skip this one").
4. Only once approved: post it, then continue.

If this tick's poller notification arrives unattended (nobody's approved the Jira draft yet) → show the draft, write it into `pending_action` in the state file, and stop — don't relaunch any poller yet. The next turn picks up from `pending_action`, confirms it, and only relaunches polling once it's posted. `pending_action` only ever holds a Jira draft now — Slack never blocks on it.

**No exceptions on the Jira side:** not for "just an ack," not because the wording is obviously right, not because posting now and summarizing after is faster. A drafted-but-unapproved Jira comment isn't sent — don't check off its concern until it actually posts.

| Excuse | Reality |
|---|---|
| "No one replied to the Jira draft, but it's clearly right" | Silence isn't approval. No reply = no post, this tick. |
| "I'll post the Jira comment now and flag it in my summary" | Posting is the action that needs approval, not the summary after. |
| "It's just a quick fixed-and-pushed note, doesn't need the tag" | Every Slack thread post still tags whoever it's addressed to. No approval wait doesn't mean no discipline. |
| "I'll just tag the reviewer, easier than looking up who actually posted" | Tag the real author of the message you're replying to — the reviewer's id only when the reviewer is who you're actually addressing. |
| "The state file doesn't exist, so this is a fresh seed" | The file's absence proves nothing — search Slack first (Step 2.0). A missing file plus an existing thread means adopt, not re-post. |

**Every Slack message this skill posts identifies which message(s) it's replying to and tags that author's real Slack member id — never a hardcoded name or a generic "hey team."** For the seed ping and every tick reply addressing the reviewer's concerns, that's `<@U0B6M74TLBY>` (the fixed reviewer, resolved from `reviewer_id` in the state file, not typed as a literal). If a reply is instead addressing something a third party said (Step 3's "anyone else" bucket), tag *their* real member id — the one you resolved via `slack_read_user_profile` — not the reviewer's. Never tag someone whose message you aren't actually responding to. If a message is about to post and doesn't tag the actual person it's addressed to, it's not ready yet — fix that before sending, since there's no approval step left to catch it.

## Handling Slack's message-length limit

Slack rejects any single message over its length cap with `{"ok": false, "error": "msg_too_long"}` (the send tool's own limit is 5000 chars, but Slack's server-side cap can bite sooner). A tick with several concerns — each carrying a fixed-and-pushed note, an escalation note, or a reasoned explanation — can add up past that before you notice.

Before posting any Slack draft (seed ping or tick reply), check its length. If it's within limits, post it directly, same as always.

If it's too long — or the post call comes back with `msg_too_long` — split it into multiple sequential thread replies (same `thread_ts`) at concern boundaries, never by truncating content. Mark each part so the reviewer can tell it's one logical reply broken up, e.g. "(1/2)" / "(2/2)" at the start of each, and post each part in order — no approval wait on any part, same as any other Slack post. If even a single concern's own note is too long on its own, split that one further at sentence boundaries, same marking convention.

**The reverse direction is a separate, already-observed failure**: the *reviewer's own* reply can error with `⚠️ Something went wrong: … 'msg_too_long'` when what it tried to say was too long — this is the same "thinking… placeholder edited in place" transition as any other verdict, so `wait-for-verdict.sh` reports it as exit 0 same as a real reply; you only learn it's an error by reading the thread. Per review-loop's tested history: **asking it to retry has failed repeatedly — ask it to break its response into smaller parts instead**: `<@U0B6M74TLBY> break your response down into smaller parts.` If it recurs on the same round, stop asking it to self-split and instead narrow your own next trigger to fewer PRs/concerns at once — same principle as splitting our own too-long drafts above, just applied to what you ask it to review.

**A third stall**: `Sorry — no response was produced. Try rephrasing your request.` is not a verdict or a rejection — it means the request landed and produced nothing. Re-trigger in-thread with a short, specific ask (the PR link(s) plus one line on where to look) — never resend the full seed-ping-style opener, a shorter *trigger* is what clears this, not a shorter original message.

Never drop a concern's content to fit — split, don't shrink.

## Step 1 — Resolve inputs & find the PRs

1. Ticket ID from args. If missing, recommend candidates instead of asking blank: check `.shipkit/pr-loop-*.md` for existing state files (in-progress pr-loop runs from an earlier session — list any found, most recently modified first) and infer from the current branch name (`feat/AR-{num}-{slug}`) like `pre-pr` Step 1 does. Exactly one candidate → confirm it with me in one line. More than one, or a state file and branch disagree → ask via `AskUserQuestion` listing each. Neither → ask for the ticket ID plainly.
2. Reuse `review-pr` Step 1's queries to find each submodule's **staging** PR for this ticket (the one that actually needs review — `main` PRs are just the promotion, skip them in the ping). Collect repo, PR number, and URL for each.
3. Also find the **root repo's** PR — `ai-roleplay-sdd` has no staging tier, so its one open PR (branch `feat/AR-{num}-{slug}` → `main`, per `pre-pr` Step 6) is always the review target. Query it the same way as `review-pr` Step 1's submodule queries, just against the `ai-roleplay-sdd` repo and the root branch name instead of the `-fe`/`-be`/`-voice` suffixed ones. Include it in the ping alongside the submodule PRs — don't skip it the way submodule `main` PRs are skipped.
4. Fetch the live Jira ticket (`getJiraIssue`) — you'll need its description/comments as ground truth for every concern raised later. Note the PO (reporter field, or ask once if ambiguous) for Step 3's escalation path.

## Step 2 — Seed (only if no thread already exists for this ticket)

The local state file is not the source of truth for "has this been seeded" — Slack is. The file can be missing for reasons that have nothing to do with whether a thread exists: a fresh clone/worktree, a teammate ran this from another machine, or the seed post landed but the file write never happened. Checking only the file's existence causes a duplicate seed message and fragments the reviewer's replies across two threads.

0. **Before drafting anything**, search `#ent-internal` for an existing seed message for this ticket — e.g. `slack_search_public_and_private` for the ticket ID scoped to that channel, or read recent channel history for a message mentioning `AR-{num}`. Do this even when `.shipkit/pr-loop-<ticket>.md` is missing.
   - **Found one** → treat it as already seeded. Reconstruct `.shipkit/pr-loop-<ticket>.md` from it: `channel_id` (`C052QGHD337`), the message's `ts` as `thread_ts`, its permalink as `message_link`, `reviewer_id` (`U0B6M74TLBY`), `my_account_id` (your own Slack account), populate `## Concerns` from whatever thread replies already exist (mark any that read as fixed-and-pushed), `last_checked_ts` set to now, `silent_ticks: 0`, `round` counted from existing reviewer-message cycles seen, `pending_action: null`. Do not post anything. Skip the rest of this step and go straight to Step 3's loop body.
   - **Nothing found** → proceed to draft and post below, this is a genuine first seed.
1. Draft one Slack message to `#ent-internal` tagging `<@U0B6M74TLBY>`, listing the staging PR links plus the root repo PR link from Step 1, e.g.: "Hey <@U0B6M74TLBY> — AR-{num} PRs are up for review: {submodule links}, plus the root repo PR: {root link}. Let me know what you find."
2. Post it directly via the Slack send-message tool to channel `C052QGHD337` — no approval wait, per the Hard Rule. Capture the returned message link and `message_ts` — this is the thread anchor (`thread_ts`) for every reply from here on, and the "tracked" link to report back to me.
3. Write `.shipkit/pr-loop-<ticket>.md`:
   ```markdown
   # PR loop state — <ticket>
   channel_id: C052QGHD337
   thread_ts: <ts>
   message_link: <link>
   reviewer_id: U0B6M74TLBY
   my_account_id: <the Slack user id running this loop>
   po_account_id: <id or "reporter">
   last_checked_ts: <ts>
   last_checked_jira_comment_id: null
   silent_ticks: 0
   round: 0
   pending_action: null

   ## Concerns
   (none yet)
   ```
   Resolve `my_account_id` once here (the currently-authenticated Slack account posting the seed ping) — Step 3 needs it to recognize your own messages in the thread and never auto-reply to them. `last_checked_jira_comment_id` stays `null` until a needs-decision concern first posts to Jira (Step 3.5) — it's the cursor `wait-for-jira-comment.sh` needs, not used before then.

## Step 3 — Loop body (every time a background poller reports new activity, or right after seeding)

0. If `pending_action` is set (a Jira comment drafted last tick that wasn't confirmed — the only thing that ever waits now), skip straight to confirming and posting it per the Hard Rule — don't re-fetch anything until it's posted and `pending_action` is cleared.
1. **Wait for the reviewer via the event-driven waiter, not a blind sleep.** Right after posting anything that expects a reviewer response (the seed ping, or any tick reply that re-triggers them), launch in the background (`Bash(run_in_background: true)`):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/skills/pr-loop/wait-for-verdict.sh <thread_ts> "" "" <after_ts>
   ```
   **`<thread_ts>` is always the state file's `thread_ts` field — the ORIGINAL thread root — never the ts of the message you just posted.** This matters most when a tick reply lands in an *existing* thread (a re-triggered stall, or Step 2's "found an existing thread, adopt it" path): the message you just sent has its own ts, but that is a reply, not the root, and passing it is wrong. Slack's `conversations.replies` does not error on a reply's ts — it silently returns just that one message with `ok:true`, indistinguishable from "no replies yet," so the waiter would poll forever while the reviewer's answer sits unseen. (The script now catches this itself — exit 6 below — but don't rely on that catch; use the stored `thread_ts` in the first place.)
   **`<after_ts>` is the ts of the message YOU just posted this tick (the seed ping, or this round's re-trigger reply) — always pass it explicitly on round 2+.** On a fresh seed thread this can be omitted (the script defaults it to `thread_ts`, a no-op there). But on any thread that already has prior rounds in it, the thread's *last* message is already a real, non-placeholder bot answer from the *previous* round — without `after_ts` the waiter reads that stale answer as "changed" on its very first poll, before the bot has even seen the new ask. This is a distinct bug from the wrong-root-ts one above: it happens even with the correct `thread_ts`, purely because re-triggering doesn't reset what "the agent's latest message" means. Get `after_ts` from the `message_ts` your Slack-send call just returned.
   (channel/bot id/timeout all come from this folder's `config.json` — no args needed unless overriding for a one-off). Exit codes:
   - **0** — the reviewer replaced its `thinking…` placeholder, i.e. said something *after* `after_ts`. Proceed to fetch and classify the thread below.
   - **2** — timed out with only `thinking…` still showing (or nothing at all) after `after_ts` → treat as a stall: reply `<@U0B6M74TLBY> try again` (per the Hard Rule) rather than re-fetching in a loop.
   - **3** (`$SLACK_REVIEW_TOKEN` unset) or **5** (config error) → tell the user directly: this token (or `config.json`) must be fixed before this skill can poll Slack at all. There's no `/loop` fallback for this path anymore — stop until it's configured.
   - **4** — Slack rejected the call (bad token / bot not in channel) → tell me, don't silently keep retrying.
   - **6** — `<thread_ts>` you passed was itself a reply, not the thread root. The error prints the real root ts — re-run the waiter with that value (and fix whatever computed the wrong ts, per the note above).
1b. **Concurrently, if any concern is `awaiting PO decision`** (a needs-decision concern already escalated to Jira per Step 3.5, not yet resolved), ALSO launch in the background, alongside 3.1 rather than instead of it:
    ```bash
    ${CLAUDE_PLUGIN_ROOT}/skills/pr-loop/wait-for-jira-comment.sh <ticket> <last_checked_jira_comment_id>
    ```
    Same exit codes as `clarify-loop` documents (0 = new comment, 2 = timeout → just relaunch, 3 = missing Jira creds → tell the user, stop, 4 = Jira error → tell the user). Whichever of the two background jobs (this one or 3.1's) reports back first is what triggered this tick — read and process both sources in step 2 below regardless of which one fired, since a single tick can resolve concerns on both tracks at once.
2. Read the state file. Fetch **all** thread replies newer than `last_checked_ts` (don't filter the fetch to `reviewer_id` — anyone can reply in this thread; this is also how a PO or third party's message is caught, since the waiter above only unblocks on the reviewer's own message), and separately check the Jira ticket for comments newer than `last_checked_jira_comment_id` if a needs-decision concern is still open (this is what 1b's poller is watching). For each new message, read its actual author id off the message payload — never assume who sent it. Bucket each by author before doing anything else:
   - **`reviewer_id` (U0B6M74TLBY)** → this is a review comment; continue to step 4 below.
   - **`my_account_id`** → this is you, not the reviewer. Skip it entirely — never draft or post an automatic reply to your own message, and don't count it as reviewer input for any concern.
   - **anyone else** → someone other than the reviewer posted in the thread (PO, teammate, etc.). Don't force it into the reviewer's fix/escalate/not-issue triage below — first resolve who they are (`slack_read_user_profile` on the author id) so you actually know who you're dealing with, then surface their message to me and ask how to proceed rather than auto-classifying or auto-replying to them. If I tell you to reply to them, that reply tags *their* real member id, not the reviewer's — per the Hard Rule above.
3. No new reviewer message and no new PO comment → increment `silent_ticks`, skip to Step 4.
4. New reviewer message(s) → reset `silent_ticks` to 0, increment `round` by 1 (one round = one new-reviewer-message triage-and-reply cycle — a tick where nothing new arrived, step 3 above, is not a round). Before doing anything else: **if `round` now exceeds `loop.max_rounds` from `config.json` (default 5), stop and escalate** — do not triage this message, do not fix, do not post. Tell me the round cap was hit, list every concern still open (from prior rounds and whatever's in this message, unclassified), and go straight to Step 4's round-limit branch. This is a hard stop, not a nudge to "wrap it up faster."
   Otherwise, **check for approval first**: if a reviewer message is an unconditional sign-off ("LGTM", "approved", "looks good", "ship it," or similar) with no new concern riding along in the same message → this ends the loop. Don't split it into concerns. Any still-open "not an issue" concern is now implicitly accepted (the reviewer replied instead of disputing) — check it off. Draft one short Slack thread reply tagging `<@U0B6M74TLBY>` acknowledging the sign-off and post it directly, then go straight to Step 4's "every concern checked off" path — **except** any concern still awaiting a PO decision on Jira: the reviewer's approval doesn't resolve that (it's a separate track), so tell me it's still open and needs following up outside this loop rather than silently dropping it. A message that pairs praise with a new ask ("LGTM once X is fixed") is not a sign-off — treat it as a normal concern below.
   Otherwise, split the message(s) into distinct concerns (a numbered/bulleted review comment = one concern each). For each new concern, apply the debate rule above (read the real diff, read the real ticket) and classify into exactly one bucket from the Hard Rule.
5. Act per bucket:
   - **Real defect, fixable** → apply the fix via `review-pr` Steps 3–5 (correct submodule dir, preserve `REQ-SDD-NNN` citations, minimal diff, run that submodule's checks, commit citing the concern, push — this auto-updates the open PR). No approval needed for the fix itself.
   - **Needs a product decision** → draft a Jira comment (business language — what decision is needed, in what situation, with options; no field/table/endpoint names) tagging the PO, confirm per the Hard Rule, post. Once posted, build its permalink — `{Jira base URL}/browse/{TICKET}?focusedCommentId={comment id}` (the comment-post response returns the new comment's id) — you'll need it for the Slack reply below. Set `last_checked_jira_comment_id` to that same id (so 1b's poller waits for whatever comes *after* it) and launch `wait-for-jira-comment.sh` per Step 3.1b if it isn't already running for this ticket. The concern stays open until the PO replies; when they do, apply their choice (fix via the same path if it requires code, or just close if it doesn't).
   - **Not an issue** → draft the explanation, grounded in the real code/ticket requirement, ready to fold into the thread reply below.
6. Draft exactly one Slack thread reply covering everything from this tick: a factual fixed-and-pushed note per defect, a "flagged to PO, will follow up" note per needs-decision concern **with the Jira comment's permalink from step 5 right there in the note** (not just a bare mention that it was escalated — the reviewer shouldn't have to go find it), the reasoned explanation per not-an-issue concern. One reply, not one per concern. This reply is addressed to the reviewer (their concerns are what it responds to), so tag `<@U0B6M74TLBY>` — resolved from `reviewer_id`, per the Hard Rule above, not just because it's the seed-ping default. Skip drafting only when step 3 fired — truly nothing new this tick.
7. Post it directly (`thread_ts` reply, no approval wait), update `last_checked_ts` to the newest reviewer message seen (and `last_checked_jira_comment_id` to the newest Jira comment seen, if a PO reply was processed this tick), clear `pending_action`, rewrite the state file with each concern's status:
   ```markdown
   ## Concerns
   - [x] <defect concern> — fixed, <commit/PR link>
   - [ ] <needs-decision concern> (escalated to Jira, awaiting PO — <jira comment permalink>)
   - [ ] <not-an-issue concern> (explained, awaiting reviewer ack/dispute)
   ```
8. If the reviewer disputes a not-an-issue explanation with new information, or a needs-decision reply from the PO doesn't cleanly match what was asked → reopen that concern and redo step 4's classification from scratch. Don't just restate the old answer.

## Step 4 — Continue or stop

- **Round cap hit** (`round > loop.max_rounds` from `config.json`, default 5) → **stop-and-report, not a silent exit.** Tell the user plainly that review went `max_rounds` rounds without reaching an unconditional sign-off, list every concern still open (fixed/escalated/explained status per the state file, plus whatever arrived in the message that triggered the cap), and stop — don't relaunch any background poller. Do **not** delete the state file — this isn't done, it's escalated; a human decides whether to keep going, raise `loop.max_rounds`, or step in directly. Never respond to hitting the cap by rushing the remaining concerns through to close them out faster — that defeats the reason it exists.
- **Every concern checked off** (fixed, PO decision applied, or not-an-issue explained with no dispute) → tell the user it's done, delete the state file. Nothing to relaunch.
- **Still open, round cap not yet hit** → if `silent_ticks` just reached 6, tell the user once. Otherwise tell the user what changed this tick. Relaunch whichever background poller(s) are still relevant: `wait-for-verdict.sh` per Step 3.1 (always — you're always waiting on the reviewer's next message) and, if any concern is still `awaiting PO decision`, `wait-for-jira-comment.sh` per Step 3.1b too. Both can run concurrently; nothing to schedule — whichever notifies first drives the next tick.

## Notes

- This resolves review *concerns*, not PR merge state — merging, approving, and closing PRs are left to the user.
- Fixing a concern doesn't end the loop if others are still open — check that one line off and keep polling for the rest.
- "Not an issue" is a claim until the reviewer accepts it (or goes silent past the escalation threshold) — don't stop polling just because you're confident.
