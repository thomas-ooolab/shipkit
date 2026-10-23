# /pr — Phase 2: review loop (Slack reviewer + Jira PO decisions)

> Loaded by `/pr` right after Phase 1's report, or directly on the resume shortcut (`.shipkit/pr-<TICKET>.md` exists). Step numbers below are the ones SKILL.md and the state file refer to.

# Phase 2 — Review loop

Fixed reviewer for this phase: the Slack user and channel in `skills/pr/config.json` — `slack.bot_reviewer_user_id` (`<reviewer_id>` below), `slack.bot_reviewer_handle`, `slack.bot_review_channel.id` (`<channel_id>`) and `.name` (the review channel). Read them from there once and keep them in the state file; never type them as literals.

## Posting to Slack (every post in this phase)
Every write to Slack or Jira goes through the plugin's scripts, never an MCP write tool (`${CLAUDE_PLUGIN_ROOT}/references/write-through-scripts.md`).
The reviewer bot ignores messages sent through the Slack MCP and only answers Slack **user-token**
posts, and the review channel may be externally shared (Slack Connect) so MCP sends are blocked there. **Never use
`slack_send_message`.** Every post — seed ping, tick reply, sign-off ack — goes through the shared
`/developer` poster (`<THREAD_TS>` = the thread root, or `-` for the seed ping that starts one):
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/post-slack.js" <channel_id> <THREAD_TS|-> <<'EOF'
<message text>
EOF
```
It prints `OK ts=<ts>` — keep that `ts`. Non-zero exit → surface the message, don't retry blindly
(**3** `SLACK_REVIEW_TOKEN` unset · **4** Slack rejected, e.g. `msg_too_long`). Read a thread with `conversations.replies` (`channel`, `ts=<thread root>`) and the channel
with `conversations.history`, same token. Resolve `my_account_id` with `auth.test` (`user_id`).
**Token rules:** read `SLACK_REVIEW_TOKEN` from the environment only — never write it to a file, the
state file, or a log, never `echo` it or enable `set -x`. Unset → tell the user to export it and stop.

Composes existing pieces — do not reimplement any of them:
- **REQUIRED:** `superpowers:systematic-debugging` — trace each raised concern to the real code path before classifying it. Never classify from the reviewer's wording alone.
- **REQUIRED for any code fix:** `/assign` — every step that changes code in response to the reviewer runs through it (Step 5 below), never an inline edit. Its fix task tells the agent: `superpowers:test-driven-development` (regression test first), minimal fix, preserve `REQ-NNN` citations, run that submodule's checks, commit citing the concern (workers never push; `/assign` pushes once it accepts). Don't re-derive any of that here.
- `bugfix`'s state-file/`silent_ticks` shape, applied to a Slack thread instead of a Jira comment thread — but **not** its `ScheduleWakeup` backoff. Like `clarify`, this phase polls via background bash scripts instead of `/loop`'s `ScheduleWakeup`, which reloads the whole session's context on every tick even when nothing changed.
- **REQUIRED:** the shared `scripts/wait-for-slack-reply.sh --until verdict` (same engine `/developer` uses with `--until others`) + this folder's `verdict-predicate.py` (the waiter's logic). Use it verbatim for "has the reviewer replied yet?" instead of blind fixed-interval polling — see Step 3 below. It reads its channel/bot id/tunables from this folder's own `config.json` — don't hardcode those values anywhere else.
- **REQUIRED for the Jira PO-decision check:** `wait-for-jira-comment.sh` (shared at `${CLAUDE_PLUGIN_ROOT}/scripts/` — one script, one source of truth). No `ScheduleWakeup` anywhere in this skill, and no fallback when a token is missing: `SLACK_REVIEW_TOKEN` and `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` are hard requirements now, same as they are for `clarify`.

State lives in `.shipkit/pr-<ticket>.md`.

## Hard rule: debate every concern, don't just accept it

A review comment is a claim, not a fact. Before classifying anything, read the actual diff for the file/line in question and pull the live Jira ticket (`getJiraIssue` — description, comments, linked tickets; not just the local `spec.md`, which can drift). Weigh the reviewer's claim against what the code and the ticket actually say. Three outcomes only, and the ticket/code decide which:

- **Real defect, no product call needed** — the code contradicts the ticket's own stated requirement, or its own stated intent, plainly and without ambiguity → fix it.
- **Real issue, needs a product decision** — could be intentional or wrong depending on unstated business intent, or more than one valid fix exists → escalate to Jira, don't fix yet.
- **Not an issue** — the code does exactly what the ticket asked for, or the reviewer's claim doesn't hold up against the real implementation → say so, with the reasoning, not just "not a bug."

A concern that's actually correct doesn't become "needs a decision" just because it's easier to punt. A concern that's genuinely ambiguous doesn't become "not an issue" just because you'd rather not open a Jira thread. Classify on what you find, not on what's convenient.

## Hard rule: Slack posts directly, Jira posts need my confirmation first

These are not symmetric. A Slack thread reply is fast-moving, cheap to follow up on, and read only by the reviewer and whoever's in the review channel; a Jira comment is a durable, org-visible record on the ticket itself, and the one that pulls the PO in to make a call. Slack messages post without waiting on me. Jira comments still do.

**Slack: draft it, tag correctly, post it (per *Posting to Slack*) — no approval wait.** Fixing a real defect never needed approval (that's code); now the message describing it, the tick-reply summary, the not-an-issue explanation, and the sign-off ack don't either. Still apply the tagging rule below and the debate/classification discipline elsewhere in this skill — "no approval needed" is not "skip the thinking," it's "don't pause for a yes before sending." Every Slack draft, the seed ping included, goes through `${CLAUDE_PLUGIN_ROOT}/references/humanize-text.md` before it posts.

**Jira: still draft → show me → wait for explicit approval → post.** A wake with no reply yet means no post this tick. The draft shown for approval is the one that went through `${CLAUDE_PLUGIN_ROOT}/references/humanize-text.md`.

1. Draft the comment.
2. Show me the exact text, verbatim.
3. Wait for explicit approval ("post it", "change X", "skip this one").
4. Only once approved: post it, then continue.

If this tick's poller notification arrives unattended (nobody's approved the Jira draft yet) → show the draft, save it as `.shipkit/pr-<ticket>-draft.md` (never the scratchpad or `/tmp`), put that path into `pending_action` in the state file, and stop — don't relaunch any poller yet. The next turn picks up from `pending_action`, confirms it, and only relaunches polling once it's posted. `pending_action` only ever holds a Jira draft now — Slack never blocks on it.

**No exceptions on the Jira side:** not for "just an ack," not because the wording is obviously right, not because posting now and summarizing after is faster. A drafted-but-unapproved Jira comment isn't sent — don't check off its concern until it actually posts.

| Excuse | Reality |
|---|---|
| "No one replied to the Jira draft, but it's clearly right" | Silence isn't approval. No reply = no post, this tick. |
| "I'll post the Jira comment now and flag it in my summary" | Posting is the action that needs approval, not the summary after. |
| "It's just a quick fixed-and-pushed note, doesn't need the tag" | Every Slack thread post still tags whoever it's addressed to. No approval wait doesn't mean no discipline. |
| "I'll just tag the reviewer, easier than looking up who actually posted" | Tag the real author of the message you're replying to — the reviewer's id only when the reviewer is who you're actually addressing. |
| "The state file doesn't exist, so this is a fresh seed" | The file's absence proves nothing — search Slack first (Step 2.0). A missing file plus an existing thread means adopt, not re-post. |

**Every Slack message this skill posts identifies which message(s) it's replying to and tags that author's real Slack member id — never a hardcoded name or a generic "hey team."** For the seed ping and every tick reply addressing the reviewer's concerns, that's `<@<reviewer_id>>` (the fixed reviewer, resolved from `reviewer_id` in the state file, not typed as a literal). If a reply is instead addressing something a third party said (Step 3's "anyone else" bucket), tag *their* real member id — the one you resolved via `slack_read_user_profile` — not the reviewer's. Never tag someone whose message you aren't actually responding to. If a message is about to post and doesn't tag the actual person it's addressed to, it's not ready yet — fix that before sending, since there's no approval step left to catch it.

**A message that asks the reviewer to review is one line: `<@<reviewer_id>>` + `slack.review_ask` (`full review <links>`), `{links}` replaced by the PR link(s) of that review — every review target (Step 1), space-separated, or the one PR in per-PR mode (`per-pr-review.md`).** The bot only starts a full review on `full review <Bitbucket PR link>` (a prose request makes it answer "Which PR?", and a feature that spans repos needs its FE and BE links together), and it takes **only the links** from that message: a list or a sentence around them is ignored. Seen at AR-583 round 6: the trigger said which items were already answered, and the bot still raised the same race dispute for the 4th time. What it does read is each PR's description and the code under review, so what it must not ask again **goes in the PR description** — the *Decisions made* block (`decisions-block.md`), refreshed before every trigger — never into the Slack message. The trigger line is exact text: it is exempt from the humanize pass. That is the seed ping (Step 2), every re-trigger (Step 3.6) and the short re-trigger after a stall (below). A sign-off ack asks for nothing, so it carries no `slack.review_ask`. After a trigger the bot first posts a status line (`Running a full review of … This takes several minutes.`): that is not a verdict, and the waiter keeps waiting through it (`waiting|running`, `verdict-predicate.py`).

## Handling Slack's message-length limit

Slack rejects any single message over its length cap with `{"ok": false, "error": "msg_too_long"}` (Slack's server-side cap can bite well before the API's own limit). A tick with several concerns — each carrying a fixed-and-pushed note, an escalation note, or a reasoned explanation — can add up past that before you notice.

Before posting any Slack draft (seed ping or tick reply), check its length. If it's within limits, post it directly, same as always.

If it's too long — or the post call comes back with `msg_too_long` — split it into multiple sequential thread replies (same `thread_ts`) at concern boundaries, never by truncating content. Mark each part so the reviewer can tell it's one logical reply broken up, e.g. "(1/2)" / "(2/2)" at the start of each, and post each part in order — no approval wait on any part, same as any other Slack post. If even a single concern's own note is too long on its own, split that one further at sentence boundaries, same marking convention.

**The reverse direction is a separate, already-observed failure**: the *reviewer's own* reply can error with `⚠️ Something went wrong: … 'msg_too_long'` when what it tried to say was too long — this is the same "thinking… placeholder edited in place" transition as any other verdict, so `wait-for-slack-reply.sh --until verdict` reports it as exit 0 same as a real reply; you only learn it's an error by reading the thread. Per review-loop's tested history: **asking it to retry has failed repeatedly — ask it to break its response into smaller parts instead**: `<@<reviewer_id>> break your response down into smaller parts.` If it recurs on the same round, stop asking it to self-split and instead narrow your own next trigger to fewer PRs/concerns at once — same principle as splitting our own too-long drafts above, just applied to what you ask it to review.

**A third stall**: `Sorry — no response was produced. Try rephrasing your request.` is not a verdict or a rejection — it means the request landed and produced nothing. Re-trigger in-thread with the one-line trigger (`slack.review_ask` with the link(s)) — never resend the full seed-ping-style opener, a shorter *trigger* is what clears this, not a shorter original message.

Never drop a concern's content to fit — split, don't shrink.

## Step 1 — Review targets & ticket

1. From Phase 1's collected URLs, take each submodule's **staging** PR (the one that actually needs review — `main` PRs are just the promotion, skip them in the ping) and the **root repo's** PR (it has no staging tier, so its one open PR → its default branch is always a review target — include it, don't skip it the way submodule `main` PRs are skipped). Collect repo, PR number, and URL for each — this list is the **review-target set** for `## PR approvals` below, and each target's current **head sha** (`source.commit.hash` from the Bitbucket PR API used in Step 5) is what its approval is pinned to. (On the resume shortcut, re-discover them with the `review-pr` Step 1 queries.)
2. **REQUIRED when `PER_PR` is set** (`--per-pr`, or `mode: per-pr` in the state file) **or when a target's diff is large** (any target over `review.per_pr_file_threshold` files): Read `${CLAUDE_PLUGIN_ROOT}/skills/pr/per-pr-review.md` and follow it for the whole loop.
2b. Fetch the live Jira ticket (`getJiraIssue`) — you'll need its description/comments as ground truth for every concern raised later. Note the PO (reporter field, or ask once if ambiguous) for Step 3's escalation path.

## Step 2 — Seed (only if no thread already exists for this ticket)

The local state file is not the source of truth for "has this been seeded" — Slack is. The file can be missing for reasons that have nothing to do with whether a thread exists: a fresh clone/worktree, a teammate ran this from another machine, or the seed post landed but the file write never happened. Checking only the file's existence causes a duplicate seed message and fragments the reviewer's replies across two threads.

0. **Before drafting anything**, look in the review channel for an existing thread for this ticket — `conversations.history` (user token) for a recent message mentioning `AR-{num}`. Do this even when `.shipkit/pr-<ticket>.md` is missing.
   - **Found one** → treat it as already seeded. Reconstruct `.shipkit/pr-<ticket>.md` from it: `channel_id` (`slack.bot_review_channel.id`), the message's `ts` as `thread_ts`, its permalink as `message_link`, `reviewer_id` (`slack.bot_reviewer_user_id`), `my_account_id` (your own Slack account), populate `## Concerns` from whatever thread replies already exist (mark any that read as fixed-and-pushed), `last_checked_ts` set to now, `silent_ticks: 0`, `round` counted from existing reviewer-message cycles seen, `## PR approvals` rebuilt from the thread's verdicts by the naming rule in Step 3.4 (anything not named stays `pending`), `pending_action: null`. Do not post anything. Skip the rest of this step and go straight to Step 3's loop body.
   - **Nothing found** → proceed to draft and post below, this is a genuine first seed.
1. Refresh each PR's *Decisions made* block (`decisions-block.md`), then draft the seed message: a **reply inside a thread** (`thread_ts` required — the bot only answers in threads), to the review channel, one line — `<@<reviewer_id>>` + `slack.review_ask` with the staging PR links plus the root repo PR link from Step 1, e.g. `<@<reviewer_id>> full review <link1> <link2> <link3>`; in per-PR mode only the first target's link (`per-pr-review.md`).
2. Post it directly with `post-slack.js` (see *Posting to Slack*) to channel `<channel_id>` — no approval wait, per the Hard Rule. No thread yet → first post one plain root message for the ticket (no tag), then post the tagged ping as its reply. Capture the ping's `ts` and permalink — the **root's** `ts` is the anchor (`thread_ts`) for every reply from here on, and the "tracked" link to report back to me.
3. Write `.shipkit/pr-<ticket>.md`:
   ```markdown
   # PR loop state — <ticket>
   channel_id: <slack.bot_review_channel.id>
   thread_ts: <ts>
   message_link: <link>
   reviewer_id: <slack.bot_reviewer_user_id>
   my_account_id: <the Slack user id running this loop>
   reporter_account_id: <the PO's id — the spec's reporter_account_id, else the ticket's reporter field>
   last_checked_ts: <ts>
   last_checked_jira_comment_id: null
   silent_ticks: 0
   round: 0
   pending_action: null   # or .shipkit/pr-<ticket>-draft.md while a Jira draft waits for approval

   ## PR approvals
   - <repo> #<n> — pending
   - <root repo> #<n> — pending
   (one line per review target from Step 1; state is `pending | lgtm@<head-sha> | changes`; in per-PR mode each line also carries `round=<n>`)

   ## Concerns
   (none yet)

   ## Answered findings
   (none yet — one line per finding of the bot, step 4a)
   ```
   Also write `mode: all` (or `mode: per-pr`, `per-pr-review.md`) beside `round:` above.
   Every target starts `pending`. Resolve `my_account_id` once here (`auth.test` `user_id` for `SLACK_REVIEW_TOKEN` — the account posting the seed ping) — Step 3 needs it to recognize your own messages in the thread and never auto-reply to them. `last_checked_jira_comment_id` stays `null` until a needs-decision concern first posts to Jira (Step 3.5) — it's the cursor `wait-for-jira-comment.sh` needs, not used before then.

## Step 3 — Loop body (every time a background poller reports new activity, or right after seeding)

**Report to the user only at a decision point:** a verdict is in and needs their choice, the *severity stop* below, every PR signed off, a concern for the PO that waits on them, or the round cap. Not per tick, per `/assign` worker, per wait or per relaunch — those are silent; the state file is the record.
0. If `pending_action` is set (a Jira comment drafted last tick that wasn't confirmed — the only thing that ever waits now), skip straight to confirming and posting it per the Hard Rule — don't re-fetch anything until it's posted and `pending_action` is cleared.
1. **Wait for the reviewer via the event-driven waiter, not a blind sleep.** Right after posting anything that expects a reviewer response (the seed ping, or any tick reply that re-triggers them), launch in the background (`Bash(run_in_background: true)`):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-slack-reply.sh" --until verdict <thread_ts> "" "" <after_ts>
   ```
   **`<thread_ts>` is always the state file's `thread_ts` field — the ORIGINAL thread root — never the ts of the message you just posted.** This matters most when a tick reply lands in an *existing* thread (a re-triggered stall, or Step 2's "found an existing thread, adopt it" path): the message you just sent has its own ts, but that is a reply, not the root, and passing it is wrong. Slack's `conversations.replies` does not error on a reply's ts — it silently returns just that one message with `ok:true`, indistinguishable from "no replies yet," so the waiter would poll forever while the reviewer's answer sits unseen. (The script now catches this itself — exit 6 below — but don't rely on that catch; use the stored `thread_ts` in the first place.)
   **`<after_ts>` is the ts of the message YOU just posted this tick (the seed ping, or this round's re-trigger reply) — always pass it explicitly on round 2+.** On a fresh seed thread this can be omitted (the script defaults it to `thread_ts`, a no-op there). But on any thread that already has prior rounds in it, the thread's *last* message is already a real, non-placeholder bot answer from the *previous* round — without `after_ts` the waiter reads that stale answer as "changed" on its very first poll, before the bot has even seen the new ask. This is a distinct bug from the wrong-root-ts one above: it happens even with the correct `thread_ts`, purely because re-triggering doesn't reset what "the agent's latest message" means. Get `after_ts` from the `message_ts` your Slack-send call just returned.
   (channel/bot id/timeout all come from this folder's `config.json` — no args needed unless overriding for a one-off). Exit codes:
   - **0** — the reviewer replaced its `thinking…` placeholder, i.e. said something *after* `after_ts`. Proceed to fetch and classify the thread below. **Unless that something is only the bot's status line** (`Running a full review of … This takes several minutes.`): that is not a verdict, so there is nothing to classify — relaunch the waiter with `<after_ts>` = the status message's `ts` and keep waiting (the current waiter already does this by itself, `waiting|running`).
   - **2** — timed out (`waiter.default_timeout_minutes`, 20: a real full review takes 12–15 minutes) → read the script's message. Only `thinking…` or nothing → a stall: re-trigger per the stall rule below (never a bare `try again`). The status line `Running a full review…` showing → **not a stall**: the review is still running, so relaunch the waiter with the same `<after_ts>` and say nothing; nudging it starts a second review. Waits on the status line do not count as `silent_ticks`; after two such relaunches (40 minutes) without a verdict, tell the user once and stop relaunching.
   - **3** (`$SLACK_REVIEW_TOKEN` unset) or **5** (config error) → tell the user directly: this token (or `config.json`) must be fixed before this skill can poll Slack at all. There's no `/loop` fallback for this path anymore — stop until it's configured.
   - **4** — Slack rejected the call (bad token / bot not in channel) → tell me, don't silently keep retrying.
   - **6** — `<thread_ts>` you passed was itself a reply, not the thread root. The error prints the real root ts — re-run the waiter with that value (and fix whatever computed the wrong ts, per the note above).
1b. **Concurrently, if any concern is `awaiting PO decision`** (a needs-decision concern already escalated to Jira per Step 3.5, not yet resolved), ALSO launch in the background, alongside 3.1 rather than instead of it:
    ```bash
    ${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-jira-comment.sh <ticket> <last_checked_jira_comment_id>
    ```
    Same exit codes as `clarify` documents (0 = new comment, 2 = timeout → just relaunch, 3 = missing Jira creds → tell the user, stop, 4 = Jira error → tell the user). Whichever of the two background jobs (this one or 3.1's) reports back first is what triggered this tick — read and process both sources in step 2 below regardless of which one fired, since a single tick can resolve concerns on both tracks at once.
2. Read the state file. Fetch **all** thread replies newer than `last_checked_ts` (don't filter the fetch to `reviewer_id` — anyone can reply in this thread; this is also how a PO or third party's message is caught, since the waiter above only unblocks on the reviewer's own message), and separately check the Jira ticket for comments newer than `last_checked_jira_comment_id` if a needs-decision concern is still open (this is what 1b's poller is watching). Also re-read every review target's current head sha; an `lgtm@<sha>` whose sha no longer matches the PR's head goes back to `pending` (new commits invalidate the approval). For each new message, read its actual author id off the message payload — never assume who sent it. Bucket each by author before doing anything else:
   - **`reviewer_id`** → this is a review comment; continue to step 4 below.
   - **`my_account_id`** → this is you, not the reviewer. Skip it entirely — never draft or post an automatic reply to your own message, and don't count it as reviewer input for any concern.
   - **anyone else** → someone other than the reviewer posted in the thread (PO, teammate, etc.). Don't force it into the reviewer's fix/escalate/not-issue triage below — first resolve who they are (`slack_read_user_profile` on the author id) so you actually know who you're dealing with, then surface their message to me and ask how to proceed rather than auto-classifying or auto-replying to them. If I tell you to reply to them, that reply tags *their* real member id, not the reviewer's — per the Hard Rule above.
3. No new reviewer message and no new PO comment → increment `silent_ticks`, skip to Step 4.
4. New reviewer message(s) → reset `silent_ticks` to 0, increment `round` by 1 (one round = one new-reviewer-message triage-and-reply cycle — a tick where nothing new arrived, step 3 above, is not a round). Before doing anything else: **if `round` now exceeds `loop.max_rounds` from `config.json` (default 5), stop and escalate** — do not triage this message, do not fix, do not post. Tell me the round cap was hit, list every concern still open (from prior rounds and whatever's in this message, unclassified), and go straight to Step 4's round-limit branch. This is a hard stop, not a nudge to "wrap it up faster."
   Otherwise, **check for approval first**: a reviewer message that is an unconditional sign-off ("LGTM", "approved", "looks good", "ship it," or similar) with no new concern riding along is **not** the end of the loop by itself — first work out **which PRs it approves**. Read the verdict text and mark `lgtm@<head-sha>` in `## PR approvals` **only for PRs it names** (by PR id, link, or repo, ideally with a head sha). "Not checked", "did not re-review X", or a PR the verdict simply doesn't mention means that PR is **not** approved — leave it `pending`. A generic LGTM that names no PR covers **none**: treat every target as `pending` and ask the bot which PRs it reviewed. A message that pairs praise with a new ask ("LGTM once X is fixed") is not a sign-off — treat it as a normal concern below.
   - **Any target still `pending`** → don't end the loop and don't ack it as final. Post one trigger tagging `<@<reviewer_id>>` — `slack.review_ask` with the link of each missing PR **on its own** (per-PR, as in `per-pr-review.md`), never a prose request. Update `last_checked_ts`, then relaunch `wait-for-slack-reply.sh --until verdict` with `after_ts` = that reply's `ts` (Step 3.1). The bot's answer counts toward `round` like any reviewer message (so `loop.max_rounds` still bounds this), but if it only confirms coverage with no new concern there's nothing to triage — just update `## PR approvals` and continue.
   - **Every target `lgtm@<current head sha>`** (or I confirmed skipping one, reason noted in the state file) → the sign-off is complete. Any still-open "not an issue" concern is now implicitly accepted (the reviewer replied instead of disputing) — check it off. Post one short ack tagging `<@<reviewer_id>>`, then go to Step 4's "every concern checked off" path — **except** any concern still awaiting a PO decision on Jira: the approval doesn't resolve that (separate track), so tell me it's still open and needs following up outside this loop.
   Otherwise, split the message(s) into distinct concerns (a numbered/bulleted review comment = one concern each). For each new concern, apply the debate rule above (read the real diff, read the real ticket) and classify into exactly one bucket from the Hard Rule.
4a. **Answered ledger first — a finding already in it is skipped, not handled again.** Give every finding of the verdict a **signature**: its file path normalized (repo-relative, no leading `./`, no line number; a finding that names no file has an empty path) + `|` + its title normalized (the headline text *after* the file location, never the location itself; lowercase; the P1/P2/P3 tag, backticks, `:<line>` and `line <n>` removed; punctuation dropped; spaces collapsed; the first 12 words). A finding whose signature is already in `## Answered findings` of the state file is **skipped automatically**: no new classification, no reply, not a reason for another round or another full review — and, when its status is `not-an-issue`, `pre-existing` or `follow-up`, it is already in the *Decisions made* block (`decisions-block.md`). Every other finding is recorded there once handled: `- <signature> — fixed | not-an-issue | pre-existing | follow-up — <one-line reason> — proof: <test name | file:line>`. A finding the bot marks **UNVERIFIABLE**, or lists under "Questions for the author", is by default **not** a fix task: keep it only when you read the code yourself and find the point sound, and write that reason in the ledger. Every finding of a verdict already in the ledger → nothing is new: no triage, no trigger; an approval ends as in 4b, anything else is shown to the user once (a decision point).
4b. **Severity stop — no more full reviews once only small things are left.** Priority is the reviewer's own label (P1 / P2 / P3); an item with no label counts as P2 until the real code says otherwise, never as P3. When **all** hold: the verdict is an approval (including "approve with comments"), every remaining item is **P3, a question, or an item already answered** in an earlier round (`## Answered findings`), and no P1 or P2 is open **as the reviewer labeled it** (not as you judged it; a P1/P2 whose signature is already in the ledger is answered, not open) → **do not send `full review` again.** Classify, then fix the real items in **one** `/assign` pass (step 5), post **nothing** to the reviewer (a tagged post starts another run; steps 6–7's post is skipped, their state bookkeeping still runs), and report to the user **once**: what was fixed, what was answered, and a **follow-up list** of the items left unfixed (id, one line, why it was not worth another review) — then stop and let the user decide `/merge`. The PRs the verdict covers are those it names or comments on; a target it never mentions is not covered → not this stop, ask for its focused review in the normal loop. Mark each covered PR `lgtm@<the sha the reviewer approved> (+ nit fixes <new sha>, no re-review by design)`, check off the items already answered (a question the bot repeats is answered, not reopened) and mark the follow-ups `[x] deferred (follow-up)`, then finish as in Step 4's "every concern checked off" path: approvals table, **state file deleted as usual** — the follow-up list lives in the one report. `loop.max_rounds` stays a hard ceiling over all of this. Any P1/P2 open, or a verdict that is not an approval → the normal loop below.
5. Act per bucket:
   - **Real defect, fixable** → **run `/assign`, don't edit code here.** `/assign` runs in Orca mode when this session is in an Orca worktree (its Step 1.5 prints `transport: orca (worktree <id>)`): look for that `transport:` line in its report, and if it says `agent` inside an Orca worktree stop and report it — never fall back to the `Agent` tool or to editing the code yourself. Append one fix task per defect to the ticket's `spec.md` `## Tasks` (`- [ ] T0NN [REQ-NNN] (<submodule>) {fix: <the concern, quoted>; regression test first; keep REQ-NNN citations} — <file path>`, REQ = the requirement whose behaviour is broken), then run `/assign <TICKET> --only <the affected submodules>` **once for the whole round** and wait for its report. **Batch the round:** collect every real defect from this verdict, across all review targets, into that one pass — never one `/assign` per concern. And before running it, **sweep the PR's diff for the same kind of defect** as each one the reviewer raised (every swallowed error written as `_ =`, every mutation that does not keep its pending state, the same missing check on a sibling route) and add each hit as a task of the same pass, so one pass fixes the whole group and the bot does not find them one at a time on the next round: its agents fix, test and commit, and `/assign` pushes the accepted commits to the feature branch, which auto-updates the open PR (no `--agent` — `/assign` picks its default). No approval needed for the fix itself. The task's file paths stay inside the spec's allowlist (Phase 1 Step 4) — a fix that needs a file outside it is a needs-decision concern (re-plan), not a silent widen. If `/assign` asks about a submodule already in progress, that is the user's answer, not yours; `SPEC=none`, or `/assign` stopping or reporting `❌` for a submodule → tell the user why and leave that concern open — never fall back to fixing inline. Before running it, note each affected submodule's `HEAD` (`git -C <PATH> rev-parse HEAD`).

     **Wait, then review what `/assign` produced — its `✅` is not the verdict.** `/assign` runs in the background: do nothing else
     on these concerns (no Slack reply, no check-off) until its report for every affected submodule is in. Then read the
     real change — `git -C <PATH> log --oneline <noted HEAD>..HEAD` and `git diff <noted HEAD>..HEAD` — against the
     concern: it addresses what the reviewer said (not a neighbouring spot), a regression test for it exists and the
     submodule's checks passed, every file is inside the allowlist, nothing unrelated changed, `REQ-NNN` citations kept,
     and the branch is pushed with a clean tree. All hold → check the concern off. Any one fails → append a follow-up fix
     task naming exactly what is missing and run `/assign` again for that submodule (at most 2 re-runs per concern); still
     failing → leave it open and tell the user what the agent produced and why it was not accepted. Never reply to the
     reviewer that it is fixed on the strength of the agent's report alone.
   - **Needs a product decision** → draft a Jira comment (business language — what decision is needed, in what situation, with options; no field/table/endpoint names) tagging the PO as `@[Name](<PO accountId>)`, confirm per the Hard Rule, post with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" post <TICKET> --file .shipkit/pr-<ticket>-draft.md` (If `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` are unset (script exits 3), fall back to `addCommentToJiraIssue` and warn the user that mentions will NOT notify anyone. Exit 5 = posted but a mention didn't land — tell the user (the comment id is still printed).). Once posted, use the `url` it prints as the permalink (`{Jira base URL}/browse/{TICKET}?focusedCommentId={comment id}`; `id` is the new comment's id) — you'll need it for the Slack reply below. Set `last_checked_jira_comment_id` to that same id (so 1b's poller waits for whatever comes *after* it) and launch `wait-for-jira-comment.sh` per Step 3.1b if it isn't already running for this ticket. The concern stays open until the PO replies; when they do, apply their choice (fix via the same path if it requires code, or just close if it doesn't).
   - **Not an issue** → draft the explanation, grounded in the real code/ticket requirement, ready to fold into the thread reply below.
6. **Refresh the *Decisions made* block, then send the trigger — nothing else.** Before every `full review` (the seed ping too), update each PR's description (`decisions-block.md`: every PR of the ticket, children and root) with what is answered so far, from `## Answered findings` and the spec. The trigger is the one line of the Hard Rule above: the bot ignores everything else in the message, so no list, no fixed-and-pushed notes, no explanations. A needs-decision item escalated to Jira goes in the block as `awaiting PO — <Jira comment permalink>`. Skip the trigger only when step 3 fired — truly nothing new this tick.
7. Post it directly (`thread_ts` reply, no approval wait), update `last_checked_ts` to the newest reviewer message seen (and `last_checked_jira_comment_id` to the newest Jira comment seen, if a PO reply was processed this tick), clear `pending_action`, rewrite the state file with each concern's status:
   ```markdown
   ## Concerns
   - [x] C1 <defect concern> — fixed, <commit/PR link> — proof: <test name | file:line>
   - [ ] C2 <needs-decision concern> (escalated to Jira, awaiting PO — <jira comment permalink>)
   - [ ] C3 <not-an-issue concern> (explained, awaiting reviewer ack/dispute) — proof: <test name | file:line>
   ```
8. If the reviewer disputes a not-an-issue explanation with new information, or a needs-decision reply from the PO doesn't cleanly match what was asked → reopen that concern and redo step 4's classification from scratch. Don't just restate the old answer.

## Step 4 — Continue or stop

- **Round cap hit** (`round > loop.max_rounds` from `config.json`, default 5) → **stop-and-report, not a silent exit.** Tell the user plainly that review went `max_rounds` rounds without reaching an unconditional sign-off, list every PR not yet `lgtm@<current sha>` (from `## PR approvals`) and every concern still open (fixed/escalated/explained status per the state file, plus whatever arrived in the message that triggered the cap), and stop — don't relaunch any background poller. Do **not** delete the state file — this isn't done, it's escalated; a human decides whether to keep going, raise `loop.max_rounds`, or step in directly. Never respond to hitting the cap by rushing the remaining concerns through to close them out faster — that defeats the reason it exists.
- **Every concern checked off** (fixed, PO decision applied, or not-an-issue explained with no dispute) **and every review target `lgtm@<its current head sha>`** (or one I explicitly confirmed skipping, reason noted) → print the approvals table (`repo #PR — state@sha`, one row per target, not just "done"), then delete the state file. Concerns done but a target still `pending`/`changes` is **not** done — keep the loop going per Step 3.4. Nothing to relaunch. `Next:` is written only when it differs from this skill's obvious default; otherwise `Next: none`. The default is `/merge <TICKET>` (it merges the signed-off child PRs, bumps and merges the root PR, moves the ticket), so normally `Next: none`; write `/bump-submodule <path>@<sha> … --closes <TICKET>` only when the user merges by hand.
- **Still open, round cap not yet hit** → if `silent_ticks` just reached 6, tell the user once. Otherwise say nothing about this tick (no per-tick report). Relaunch whichever background poller(s) are still relevant: `wait-for-slack-reply.sh --until verdict` per Step 3.1 (always — you're always waiting on the reviewer's next message) and, if any concern is still `awaiting PO decision`, `wait-for-jira-comment.sh` per Step 3.1b too. Both can run concurrently; nothing to schedule — whichever notifies first drives the next tick.
