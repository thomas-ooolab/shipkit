---
name: clarify
description: "Use when the user wants to resolve a Jira ticket's open PO-clarification questions without manually re-checking the ticket — seeds one Jira comment with the ticket's open business-logic questions, then polls for the PO's reply on a self-paced background loop until every question is resolved. Trigger: /clarify <ticket-id>. Examples: \"clarify AR-450\", \"keep asking the PO until AR-450's open questions are resolved\""
---

# Clarify Loop

Automates the "ask PO to clarify business logic, wait, fold the answer back into the spec" cycle for one ticket, so the user doesn't have to manually re-open Jira to check for a reply.

Composes three existing pieces — do not reimplement any of them:
- `spec-from-ticket`'s ambiguity/citation logic, to find and phrase open questions
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
2. Find the ticket's spec: search `specs/*/spec.md` under the SDD root for one whose frontmatter references this ticket ID. If none exists, or it has no `## Open questions` section, invoke the `spec-from-ticket` skill on this ticket first (it produces that section) — then continue.
3. Identify the PO to tag: check the Jira ticket's reporter field via `getJiraIssue`. If it's ambiguous who the actual product owner is (reporter is a bot, or a different person owns clarifications for this project), ask the user once with `AskUserQuestion` and remember the answer for this ticket only (don't persist it globally — POs vary per project).

## Step 2 — Seed (only if no seed comment already exists on this ticket)

The local state file is not the source of truth for "has this been seeded" — the Jira ticket is. The file can be missing for reasons that have nothing to do with whether a seed comment exists: a fresh clone/worktree, a teammate ran this from another machine, or the comment posted but the file write never happened. Checking only the file's existence causes a duplicate question comment on the ticket.

0. **Before drafting anything**, fetch the ticket's comments (`getJiraIssue` with comments) and look for an existing comment tagging the PO with this ticket's open questions — do this even when `.shipkit/clarify-<ticket>.md` is missing.
   - **Found one** → treat it as already seeded. Reconstruct `.shipkit/clarify-<ticket>.md` from it: `spec` path, `po_account_id`, `last_checked_comment_id` set to that comment's ID, `pending_comment: null`, `silent_ticks: 0`, and the open-questions checklist — check off any question a later PO reply already answers (fold the answer into the spec, same as Step 3.4 would). Do not post anything. Skip the rest of this step and go straight to Step 3's loop body.
   - **Nothing found** → proceed below, this is a genuine first seed.
1. Read the spec's `## Open questions` section → list of questions, each already in the lettered-option format `spec-from-ticket` produces.
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
   pending_comment: null

   ## Open questions
   - [ ] <question text>
   - [ ] <question text>
   ```

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
3. Fetch Jira comments on the ticket newer than `last_checked_comment_id` (`getJiraIssue` with comments) — the poller only told you *something* changed, not *what*; read the actual content here.
4. Reset `silent_ticks` to 0. Match each open question against what the new comment(s) said; every question they touch falls into exactly one bucket:
   - **Clearly answered** → check it off, fold the resolution into the spec's `## Open questions` section (move to resolved/decisions, keep the answer verbatim so it's traceable).
   - **Raises a genuinely new business ambiguity** → append it to the open-questions list, phrased business-plain, to be asked as a follow-up (see below).
   - **Neither** — the PO replied but didn't answer and didn't raise a new business question (vague reply, "let me get back to you", punts the question to a third party or another team) → leave the question open, but add a short bracketed status note after it in the state file, e.g. `(blocked — PO checking with platform team)`, so the next tick has context instead of re-asking cold.
5. Draft exactly one Jira comment covering everything the PO said this tick: acknowledge it (a bucket-3 non-answer still gets a brief acknowledgment — a PO reply must never go unanswered), plus any new follow-up question from bucket 2. Reaching this step already means a new PO comment exists (Step 3.1's exit 2 branch handles the "nothing new" case) — don't skip drafting here.
6. Confirm the draft with me per the Hard Rule above before posting. If unconfirmed this turn, write it to `pending_comment`, rewrite the state file with everything else already updated (checked-off questions, `silent_ticks`, etc.), and stop here — don't relaunch the poller until it's posted.
7. Once approved, post it, update `last_checked_comment_id` to the newest comment ID seen (this is also the `<after_comment_id>` for the next poller launch), clear `pending_comment`, rewrite the state file, then relaunch the poller per Step 3.1 to keep waiting.

## Step 4 — Continue or stop

- **All open questions checked off** → update the spec (remove the `## Open questions` section or mark it fully resolved), delete `.shipkit/clarify-<ticket>.md`, tell the user it's done. Nothing to relaunch — no background poller, no `ScheduleWakeup`.
- **Still open** →
  - If `silent_ticks` just reached 6 (six poller timeouts — roughly a week of silence at the default 24h window) for the first time, say so to the user explicitly — don't just quietly keep polling.
  - Tell the user what changed this tick (resolved N, still waiting on M — list the still-open ones, including any blocked-status notes).
  - Relaunch the background poller per Step 3.1 with the current `last_checked_comment_id` — that's what keeps this loop alive now, not a scheduled wake. Nothing further to do until it reports back.

## Notes

- This is a session loop, not a cron — `wait-for-jira-comment.sh` runs as a child process of this session, so it still dies if the terminal closes. Same trade-off as before; only *how* it waits changed, not *whether* it survives closing the terminal.
- No `/loop` / `ScheduleWakeup` anywhere in this skill — the background poller is the only polling mechanism, and it requires `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` to be set (Step 3.1's exit 3).
- Don't re-post the full open-question list every tick — only the single per-tick comment described in Step 3.5, and only when the PO said something new.
