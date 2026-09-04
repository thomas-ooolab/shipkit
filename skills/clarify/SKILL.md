---
name: clarify
description: "Use when the user wants to resolve a Jira ticket's open PO-clarification questions without manually re-checking the ticket — seeds one Jira comment with the ticket's open business-logic questions, then polls for the PO's reply on a self-paced background loop until every question is resolved. Trigger: /clarify <ticket-id>. Examples: \"clarify AR-450\", \"keep asking the PO until AR-450's open questions are resolved\""
---

# Clarify Loop

Automates the "ask PO to clarify business logic, wait, fold the answer back into open-question.md" cycle for one ticket, so the user doesn't have to manually re-open Jira to check for a reply.

Composes three existing pieces — do not reimplement any of them:
- `spec-from-ticket` and `plan-deep`'s undefined-reference/dependency-chain checks, which write
  `specs/NNN-slug/open-question.md` — this skill only reads and updates that file, it never decides on
  its own what counts as an open question.
- Atlassian MCP tools, to read/post Jira comments
- **not** `/loop`'s `ScheduleWakeup` — this skill polls via `wait-for-jira-comment.sh` (colocated in this folder), a background bash script that sleeps and re-checks Jira itself. A `ScheduleWakeup` wake reloads the whole session's context every tick even when nothing changed; the background script costs one `curl` per interval and only notifies you when there's real news.

State lives in `.shipkit/clarify-<ticket>.md` at the SDD root repo, so a re-invocation picks up where it left off instead of re-seeding.

## Hard rule: business language only, both directions

Every Jira comment this skill posts — the initial question AND any follow-up reply/acknowledgment once the PO answers — must read as plain business language. No field names, table/column names, endpoint paths, ticket-internal jargon ("sync logic", "the `is_active` flag", "webhook retry"). Say what a non-technical PO would say: what decision is needed, in what situation, with what options. This applies even to comments where you're just confirming you understood the PO's answer.

Bad: "Confirming: `retention_days` defaults to 90 unless `plan_tier == enterprise`."
Good: "Got it — Enterprise workspaces keep call recordings for a year, everyone else for 90 days. Confirming that's right before I build it that way."

## Hard rule: sound like a person, not a report

Write every comment the way you'd actually type a quick reply — plain sentences, contractions, one thought running into the next. Not a bolded outline, not a numbered "questions" list, no stock phrases ("please advise", "I hope this clarifies", "kindly confirm at your earliest convenience"). Asking about more than one thing in a single comment still reads as one person talking, not a formatted document — run them together or split with "also," not a numbered heading per question.

Bad: "**Question 1:** Please confirm the retention period for Enterprise workspaces.\n**Question 2:** Please confirm whether the weekly digest should include workspaces with zero calls.\nKindly advise at your earliest convenience."
Good: "Two things I need from you — how long should Enterprise workspaces keep call recordings, a year or unlimited? And should the weekly digest still go out to workspaces that had zero calls that week, or skip them?"

## Hard rule: confirm with me before every Jira post

Never call the Jira comment-posting tool until I've explicitly approved the exact text. This applies to the seed comment and every per-tick comment — acknowledgments included, not just the substantive ones.

1. Draft the comment.
2. Show me the exact text, verbatim — not a summary of what you plan to say.
3. Wait for explicit approval ("post it", "change X", "skip this one"). A wake with no reply yet means no post this tick — don't post because "no one objected" or "this one's obviously fine, it's just an ack."
4. Only once approved: post it, then continue.

If this tick's poller notification arrives unattended (nobody's replied to the draft yet) → show the draft, write it into `pending_comment` in the state file, and stop — don't relaunch the background poller yet, since nothing new has been posted to poll replies against. The next turn (I reply, or you're re-invoked) picks up from `pending_comment`, skips straight to confirming it, and only relaunches the poller once it's posted.

**No exceptions:**
- Not for "just an acknowledgment" comments.
- Not because the wording is obviously right.
- Not because posting now and mentioning it in the summary afterward is faster.
- A drafted-but-unapproved comment is not sent. Don't count it as "resolved this tick" until it actually posts.

| Excuse | Reality |
|---|---|
| "It's just a routine ack, not worth asking about" | Every comment is public on the ticket — I decide what goes out, not you. |
| "No one replied to the draft, but it's clearly right" | Silence isn't approval. No reply = no post, this tick. |
| "I'll post now and flag it in my summary" | Posting is the action that needs approval, not the summary after. |
| "Confirming breaks the autonomous loop" | It doesn't — it pauses posting, not the whole skill. Polling and rescheduling resume normally once posted. |
| "The state file doesn't exist, so this is a fresh seed" | The file's absence proves nothing — check the ticket's comments first (Step 2.0). A missing file plus an existing seed comment means adopt, not re-post. |

## Step 1 — Resolve inputs

1. Ticket ID comes from the invocation args (e.g. `AR-450`). If missing, recommend candidates instead of asking blank: check `.shipkit/clarify-*.md` for existing state files (in-progress `/clarify` runs from an earlier session — list any found, most recently modified first) and infer from the current branch name (`feat/AR-{num}-{slug}`) like `pre-pr` Step 1 does. Exactly one candidate → confirm it with me in one line. More than one, or a state file and branch disagree → ask via `AskUserQuestion` listing each. Neither → ask for the ticket ID plainly.
2. Find the ticket's spec dir: search `specs/*/spec.md` under the SDD root for one whose frontmatter references this ticket ID, then look for `open-question.md` alongside it. If the spec doesn't exist, invoke `spec-from-ticket` first — then continue.
   **Consolidate before the first send.** If a seed comment hasn't been posted yet (Step 2.0 hasn't found one) and the spec's frontmatter `status` isn't `planned` yet, recommend running `plan-deep` first, even if `open-question.md` already has content from `spec-from-ticket` — `plan-deep`'s dependency-chain gate routinely finds *more* undefined references once it grounds in real code, and a second seed-shaped comment landing on the ticket a day after the first reads as scattered, not thought-through. Ask the user once: `["Run /plan-deep first so every open question goes out in one pass, or seed with what's here now?", "Run /plan-deep first", "Seed now with what's here"]`. If the spec is already `status: planned` (or the user chooses to seed now), proceed — nothing further to consolidate.
3. Identify the PO to tag: check the Jira ticket's reporter field via `getJiraIssue`. If it's ambiguous who the actual product owner is (reporter is a bot, or a different person owns clarifications for this project), ask the user once with `AskUserQuestion` and remember the answer for this ticket only (don't persist it globally — POs vary per project).

## Step 2 — Seed (only if no seed comment already exists on this ticket)

The local state file is not the source of truth for "has this been seeded" — the Jira ticket is. The file can be missing for reasons that have nothing to do with whether a seed comment exists: a fresh clone/worktree, a teammate ran this from another machine, or the comment posted but the file write never happened. Checking only the file's existence causes a duplicate question comment on the ticket.

0. **Before drafting anything**, fetch the ticket's comments (`getJiraIssue` with comments) and look for an existing comment tagging the PO with this ticket's open questions — do this even when `.shipkit/clarify-<ticket>.md` is missing.
   - **Found one** → treat it as already seeded. Reconstruct `.shipkit/clarify-<ticket>.md` from it: `spec` path, `po_account_id`, `last_checked_comment_id` set to that comment's ID, `pending_comment: null`, `silent_ticks: 0`, `follow_up_rounds` set to the count of genuinely-new questions already asked in replies since the seed (0 if none), and the open-questions checklist — check off any question a later PO reply already answers (fold the answer into `open-question.md`, same as Step 3.4 would). Do not post anything. Skip the rest of this step and go straight to Step 3's loop body.
   - **Nothing found** → proceed below, this is a genuine first seed.
1. Read `open-question.md` → list of questions, each already in business-language / lettered-option format (`spec-from-ticket` and `plan-deep` both write to this file).
2. Translate any that still read technical (they shouldn't, if `spec-from-ticket` wrote them, but re-check) into plain business language per the rule above.
3. Draft ONE comment tagging the PO with every open question, then confirm it with me per the Hard Rule above. If unconfirmed this turn, write it as `pending_comment` in the state file below and stop — don't launch the background poller yet.
4. Once approved, post via `addCommentToJiraIssue`. Note the posted comment's ID (or ticket's current latest comment ID if the API doesn't echo it back) as `last_checked_comment_id`, and clear `pending_comment`.
5. Write `.shipkit/clarify-<ticket>.md`:
   ```markdown
   # Clarify loop state — <ticket>
   spec: specs/<NNN-slug>/spec.md
   po_account_id: <id or "reporter">
   last_checked_comment_id: <id>
   silent_ticks: 0
   follow_up_rounds: 0
   pending_comment: null

   ## Open questions
   - [ ] OQ-1 — <question text>
   - [ ] OQ-2 — <question text>
   ```
   Ids mirror `open-question.md`'s — same `OQ-N`, same order, so a question is traceable across both
   files and any Jira comment/spec reference to it. Carry over the `[no-precedent]` tag verbatim on any
   item that has one (see spec-from-ticket/plan-deep) — it's what tells Step 3.4 to treat that item's
   eventual answer as lower-confidence. `follow_up_rounds` counts ticks where Step 3.4
   fired a genuinely-new question (bucket 2) — see the round cap in Step 3.4.

## Step 3 — Loop body (every time the background poller reports new activity, or right after seeding)

0. If `pending_comment` is set (a draft from an earlier tick wasn't confirmed yet), skip straight to confirming and posting it per the Hard Rule above — don't relaunch the poller or reclassify anything until it's posted and `pending_comment` is cleared.
1. **Wait for the PO via the background poller, not a fixed-interval `/loop` wake.** Right after seeding, or after posting any tick reply, launch in the background (`Bash(run_in_background: true)`):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/skills/clarify/wait-for-jira-comment.sh <ticket> <last_checked_comment_id>
   ```
   This sleeps and re-checks Jira itself (default: every 60s, up to a 24h window) instead of paying for a full session wake on every empty check — you're notified once, only when something actually posted. Exit codes:
   - **0** — a new comment landed. Continue to step 2 below.
   - **2** — timed out with nothing new → increment `silent_ticks` (see Step 4), then relaunch the same command with the same `<last_checked_comment_id>` to keep waiting. Normal for a quiet ticket, not a failure.
   - **3** (`JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` unset) → tell the user directly these are required to poll Jira at all — there's no `/loop` fallback for this path anymore. Stop until they're configured (see the ecc `jira-integration` skill for how to mint a token).
   - **4** — Jira rejected the request (bad auth / wrong ticket key) → tell the user, don't silently keep retrying.
2. Read the state file.
3. Fetch Jira comments on the ticket newer than `last_checked_comment_id` (`getJiraIssue` with comments) — the poller only told you *something* changed, not *what*; read the actual content here. **Check each new comment's author against `po_account_id` first.** A reply from someone other than the tagged PO is not automatically authoritative — same Jira ticket, different person than the one asked. Don't fold a mismatched-author reply into `open-question.md` as a resolved answer; when drafting this tick's comment/summary (step 5 below), say plainly who the tagged PO was and who actually replied, and let the user decide whether to treat it as authoritative, wait for the named PO, or escalate. **Also re-read `open-question.md`** and diff it against the state file's checklist — a later `/plan-deep` run (or a manual edit) can append new items after this ticket was already seeded, and those need to reach the PO in this tick's comment too, not sit unasked. Any item in the file not yet in the state file's checklist is new: add it to today's batch the same as a bucket-2 item below (it doesn't count against `follow_up_rounds` — that counter is only for questions *this skill itself* generated in response to a PO reply, not ones `spec-from-ticket`/`plan-deep` already decided were needed).
4. Reset `silent_ticks` to 0. Match each open question against what the new comment(s) said; every question they touch falls into exactly one bucket:
   - **Clearly answered** → before checking it off, separate what the PO actually decided from how they happened to phrase it. A PO answering in casual/UI-sounding words ("dropdown", "a popup", "checkbox list") is very often describing a business rule (cardinality, required/optional, the fixed value set) in whichever UI term came to mind, not approving an implementation. If `specs/NNN-slug/design-contract.md` doesn't exist for this ticket (no design reference), do not record the UI word as a confirmed spec — fold in the business rule only, and note the replier's literal wording separately as unconfirmed phrasing, not as a design decision. If the item carries `[no-precedent]` (no existing precedent anywhere in the codebase — the reply is inventing a definition, not confirming one), keep the tag on the resolved line and say so explicitly in this tick's comment/summary: this is lower-confidence than a normal answered question, since there's nothing in the codebase to validate the reply against. Then check it off in both the state file and `open-question.md` (keep the answer verbatim next to the item so it's traceable — don't delete the resolved line, mark it resolved).
   - **Raises a genuinely new business ambiguity** → first check whether it's actually a **sub-detail of an already-open question** (fold it into that item's discussion instead of creating a new one — most PO replies that sound like "one more thing" are refining something already asked, not opening new ground). Only if it's a genuinely distinct gap: append it to `open-question.md` as the next `OQ-N` (continue the file's existing numbering — never renumber or reuse an id) and to the state file's checklist, phrased business-plain, subject to the round cap below.
   - **Neither** — the PO replied but didn't answer and didn't raise a new business question (vague reply, "let me get back to you", punts the question to a third party or another team) → leave the question open, but add a short bracketed status note after it in the state file, e.g. `(blocked — PO checking with platform team)`, so the next tick has context instead of re-asking cold.

   **Round cap on new questions — no unbounded branching.** If this tick would add a genuinely-new bucket-2 question, increment `follow_up_rounds` first. If it would now exceed 3: do **not** add the new question this way. Instead, fold it into a single closing summary — everything still open, including this last item, phrased as one consolidated ask — and say so to the user: "hit the follow-up cap (3 rounds) — asking everything outstanding in one final comment instead of opening another round; if the PO's answer raises something further, that's a manual follow-up, not another auto-generated tick." This mirrors `pr`'s `max_rounds` — the point is the same: a chain of one-new-question-per-reply is a design smell, not a feature.
5. Draft exactly one Jira comment covering everything the PO said this tick: acknowledge it (a bucket-3 non-answer still gets a brief acknowledgment — a PO reply must never go unanswered), plus any new/re-synced question from this tick. Reaching this step already means a new PO comment exists (Step 3.1's exit 2 branch handles the "nothing new" case) — don't skip drafting here.
6. Confirm the draft with me per the Hard Rule above before posting. If unconfirmed this turn, write it to `pending_comment`, rewrite the state file with everything else already updated (checked-off questions, `silent_ticks`, etc.), and stop here — don't relaunch the poller until it's posted.
7. Once approved, post it, update `last_checked_comment_id` to the newest comment ID seen (this is also the `<after_comment_id>` for the next poller launch), clear `pending_comment`, rewrite the state file, then relaunch the poller per Step 3.1 to keep waiting.

## Step 4 — Continue or stop

- **All open questions checked off** → mark every item in `open-question.md` resolved (or delete the file — either is fine, nothing else reads it once empty), delete `.shipkit/clarify-<ticket>.md`, tell the user it's done. If any resolved item carried `[no-precedent]`, call those out separately in the done message — e.g. "OQ-1 is answered but was net-new with nothing in the codebase to check it against; confirm directly with the PO before implementation relies on it." Don't let a no-precedent resolution look identical to a normal one. Nothing to relaunch — no background poller, no `ScheduleWakeup`.
- **Follow-up round cap just hit** (`follow_up_rounds` reached 3 this tick) → this tick's comment was already the consolidated closing ask (Step 3.4). Tell the user plainly: the cap was hit, list every question still open (including the one just folded in), and say that any further new ambiguity from here is a manual follow-up, not another auto-generated round. Still relaunch the poller (below) — the loop keeps polling for answers to what's already been asked, it just stops *generating new questions* on its own.
- **Still open** →
  - If `silent_ticks` just reached 6 (six poller timeouts — roughly a week of silence at the default 24h window) for the first time, say so to the user explicitly — don't just quietly keep polling.
  - Tell the user what changed this tick (resolved N, still waiting on M — list the still-open ones, including any blocked-status notes).
  - Relaunch the background poller per Step 3.1 with the current `last_checked_comment_id` — that's what keeps this loop alive now, not a scheduled wake. Nothing further to do until it reports back.

## Notes

- This is a session loop, not a cron — `wait-for-jira-comment.sh` runs as a child process of this session, so it still dies if the terminal closes. Same trade-off as before; only *how* it waits changed, not *whether* it survives closing the terminal.
- No `/loop` / `ScheduleWakeup` anywhere in this skill — the background poller is the only polling mechanism, and it requires `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` to be set (Step 3.1's exit 3).
- Don't re-post the full open-question list every tick — only the single per-tick comment described in Step 3.5, and only when the PO said something new.
- **Consolidation, not a drip feed.** Step 1.2 pushes to run `plan-deep` before the first seed so both sources' questions go out together; Step 3.4's round cap (`follow_up_rounds`, max 3) stops the loop from generating an unbounded chain of one-new-question-per-PO-reply. The goal is one well-thought-out ask, not a slow trickle.
