---
name: bugfix-loop
description: "Use when a tester/QA posts a Jira comment reporting a bug on an in-flight feature ticket (the comment, not the ticket's own description, is the bug report) and it needs triage — deciding per reported concern whether it's a real defect (fix it), expected behavior (explain why), or a product decision (ask for options) — then tracking the commenter's reply until every concern is actually resolved, not just replied to once. Trigger: /bugfix-loop <ticket-id>. Examples: \"/bugfix-loop AR-460\", \"QA left a bug comment on AR-460, triage it and keep checking until they confirm\""
---

# Bugfix Loop

Investigate a reported bug, fix what's actually broken, explain what isn't, ask about what's genuinely unclear — then keep checking Jira until every concern the reporter raised is resolved, not just replied to once.

Composes existing pieces — do not reimplement any of them:
- **REQUIRED:** `superpowers:systematic-debugging` — trace each reported symptom to root cause before classifying it. Never classify from the ticket text alone.
- **REQUIRED for any code fix:** `superpowers:test-driven-development` — write the regression test first.
- This project's own bugfix mechanics, if it has one (e.g. a `report-bug` skill's dev flow — branch, fix, test, push, PR) — reuse its conventions, don't invent a parallel one. If none exists, just follow the repo's normal branch/commit/PR workflow.
- `clarify-loop`'s state-file/`silent_ticks` shape and business-language rule below — same mechanics, applied to bug concerns instead of spec open-questions.
- **REQUIRED:** `wait-for-jira-comment.sh` (colocated in this folder as a symlink to `clarify-loop`'s copy — one script, one source of truth, don't fork it into a bugfix-specific variant). It's a plain interval poller against the Jira REST API (no Slack bot involved), so it fits this skill exactly as-is: pass the ticket and `last_checked_comment_id`, it blocks until a new comment lands. No `/loop`/`ScheduleWakeup` anywhere in this skill — `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` are hard requirements, same as `clarify-loop`.

State lives in `.shipkit/bugfix-<ticket>.md`.

## Hard rule: business language only, both directions

Every Jira comment this skill posts must read as plain business language — no field/function/table names, endpoint paths, or code snippets, even when explaining "why this is correct behavior." Say what a non-technical reporter would understand: what happens, in what situation, why, or what decision is needed.

Bad: "`CanViewCallReview` gates on `c.RecordedAt.After(m.AssignedAt)`, so this is by design."
Good: "That's how it's built today — a manager only sees calls recorded after they joined the team, not the team's full history before that. Wanted to check: should managers see everything the team ever recorded, or only what happened since they joined?"

## Hard rule: sound like a person, not a report

Write every comment the way you'd actually type a quick reply — plain sentences, contractions, one thought running into the next. Not a bolded outline, not a numbered "findings" report, no stock phrases ("I've thoroughly investigated...", "please let me know if you have any questions", "I hope this clarifies"). Covering several concerns in one comment still reads as one person talking, not a formatted document — separate them with a line break or "also," not a bolded heading per concern.

Bad: "Looked into all three issues from testing:\n**1. Manager can't see call reviews from before they joined the team.** That's how it's built today...\n**2. Weekly digest double-counting.** Confirmed as a bug...\n**3. Export Team Performance button greyed out.** Expected, not a bug..."
Good: "Went through all three. The manager-visibility one is by design — right now a manager only sees calls recorded after they joined the team, not the team's full history before that. Wanted to check if that's actually the right call, or if managers should see everything once they're assigned — let me know which. The digest double-counting was a real bug, it was counting a call once per person instead of once per call — fixed and pushed, should be right next time. And the export button being greyed out is expected, that workspace is on the free plan and that export needs a paid tier, nothing to fix there."

## Hard rule: confirm with me before every Jira post

Never call the Jira comment-posting tool until I've explicitly approved the exact text. This applies to the seed comment and every per-tick comment — status notes and acknowledgments included, not just the substantive ones. Fixing a real-defect concern doesn't need my approval (that's code, not a public comment) — only the comment describing it does.

1. Draft the comment.
2. Show me the exact text, verbatim — not a summary of what you plan to say.
3. Wait for explicit approval ("post it", "change X", "skip this one"). A wake with no reply yet means no post this tick — don't post because "no one objected" or "this one's obviously fine, it's just an ack."
4. Only once approved: post it, then continue.

If this tick's poller notification arrives unattended (nobody's replied to the draft yet) → show the draft, write it into `pending_comment` in the state file, and stop — don't relaunch the background poller yet, since nothing new has been posted to poll replies against. The next turn (I reply, or you're re-invoked) picks up from `pending_comment`, skips straight to confirming it, and only relaunches the poller once it's posted.

**No exceptions:**
- Not for "just an acknowledgment" or "just a fixed-and-pushed note."
- Not because the wording is obviously right.
- Not because posting now and mentioning it in the summary afterward is faster.
- A drafted-but-unapproved comment is not sent. Don't count its concern as checked off until it actually posts.

| Excuse | Reality |
|---|---|
| "It's just a routine ack, not worth asking about" | Every comment is public on the ticket — I decide what goes out, not you. |
| "No one replied to the draft, but it's clearly right" | Silence isn't approval. No reply = no post, this tick. |
| "I'll post now and flag it in my summary" | Posting is the action that needs approval, not the summary after. |
| "Confirming breaks the autonomous loop" | It doesn't — it pauses posting, not the whole skill. Polling and rescheduling resume normally once posted. |
| "The state file doesn't exist, so this bug report hasn't been triaged yet" | The file's absence proves nothing — check the ticket's comments after the bug report first (Step 1.4). A missing file plus an existing response means resume, not re-triage. |

## Step 1 — Resolve inputs & investigate

1. Ticket ID from args. If missing, recommend candidates instead of asking blank: check `.shipkit/bugfix-*.md` for existing state files (in-progress bugfix-loop runs from an earlier session — list any found, most recently modified first) and infer from the current branch name (`feat/AR-{num}-{slug}`) like `pre-pr` Step 1 does. Exactly one candidate → confirm it with me in one line. More than one, or a state file and branch disagree → ask via `AskUserQuestion` listing each. Neither → ask for the ticket ID plainly. The ticket is an existing feature ticket already being built — the bug report is a **comment** on it, not the ticket's own description (that's the feature spec, unrelated to what's being triaged here).
2. Find the comment(s) to triage: if the invocation points at a specific comment, use that. Otherwise take the latest tester/QA comment that reports unexpected behavior (skip status updates, unrelated remarks) — if more than one recent comment could qualify, ask the user which one. If it lists multiple distinct problems (e.g. a numbered list), treat each as a separate concern.
3. The person to reply to is the **author of that comment** — not the ticket's Jira "Reporter" field, which is usually whoever filed the original feature ticket, not the tester who found the bug. If the comment author is ambiguous (shared/bot account), ask the user once and remember for this ticket only.
4. **Before triaging, check whether this exact bug report already has a response.** The local state file is not the source of truth for "already triaged" — the ticket's comments are. The file can be missing for reasons unrelated to whether a response exists: a fresh clone/worktree, a teammate ran this from another machine, or the response posted but the file write never happened. Fetch the ticket's comments posted *after* the bug-report comment found in step 2 and look for one from you/the bot account that already addresses it (a fixed-and-pushed note, a not-a-defect explanation, or lettered options, in this skill's own comment style — see Steps 2–3).
   - **Found one** → treat it as the already-posted tick response. Reconstruct `.shipkit/bugfix-<ticket>.md` from it: `commenter_account_id`, `po_account_id`, `seed_comment_id` (the bug-report comment), `last_checked_comment_id` set to that response comment's ID, `pending_comment: null`, `silent_ticks: 0`, and the concerns checklist with each concern's status as that comment states it. Do not re-run systematic-debugging and do not draft a new comment. Skip the rest of Step 1 and Steps 2–3 entirely — go straight to Step 4's loop body.
   - **Nothing found** → this is a genuine first triage, continue below.
5. Separately, identify the **PO** — the person who actually owns the business call on this feature. Check the ticket's reporter field first (on a feature ticket it's usually the PO); if that's wrong for this project (bot, or someone else owns product calls here), ask the user once and remember for this ticket only. You'll @-mention the PO whenever a concern needs their ruling (Step 3.3) — the tester gets acknowledged either way, but they aren't who decides.
6. Invoke `superpowers:systematic-debugging` on each concern, reading the real code path — not just reasoning from the comment's description of symptoms.

## Step 2 — Classify each concern into exactly one bucket

- **Real defect** — the code contradicts its own stated/implied intent, or produces an outcome nothing about the design supports → fix it. No explanatory comment for this concern (Step 3 posts a status note instead, not a "why").
- **Not a defect** — the code does exactly what it was deliberately built to do, and the reasoning holds up → business-language comment explaining why.
- **Needs a product decision** — the behavior could be intentional or wrong depending on unstated business intent, or multiple valid fixes exist and choosing between them is a product call → business-language comment with lettered options.

A ticket can have concerns in different buckets at once — classify each on its own merits.

## Step 3 — Act, then post ONE Jira comment for the tick

1. Fix every real-defect concern now, on the ticket's **existing feature branch** — a bug reported on an in-flight feature ticket almost always has one already; check it out per this project's normal flow (e.g. `report-bug` FLOW C's branch/test/push/PR path, if this project has that skill). Pushing there auto-updates any open PRs. Only create a new branch from the base branch (e.g. `staging`) in the rare case no feature branch exists for this ticket yet. Regression test first. Push once tests pass.
2. Leave not-a-defect and needs-decision concerns as comments only — no code changes yet.
3. Draft exactly one Jira comment covering every concern from this tick: a factual fixed-and-pushed note per defect (link the branch/PR), the business-language explanation per not-a-defect concern, the lettered options per needs-decision concern. One comment, not one per concern. Tag the **tester** throughout (they reported it, they get the update either way); additionally @-mention the **PO** on any not-a-defect or needs-decision concern — that's their ruling to make or confirm, not the tester's. Real-defect status notes don't need the PO tagged.
4. Confirm the draft with me per the Hard Rule above before posting. If unconfirmed this turn, write it to `pending_comment` in the state file below and stop — don't launch the background poller yet.
5. Once approved, post it, then write `.shipkit/bugfix-<ticket>.md`:
   ```markdown
   # Bugfix loop state — <ticket>
   commenter_account_id: <id of the tester/QA who posted the bug comment>
   po_account_id: <id or "reporter">
   seed_comment_id: <id of the comment being triaged>
   last_checked_comment_id: <id>
   silent_ticks: 0
   pending_comment: null

   ## Concerns
   - [x] <defect concern text> — fixed, <branch/PR link>
   - [ ] <not-a-defect concern text> (awaiting reporter ack)
   - [ ] <needs-decision concern text> (awaiting reporter's choice: A/B/...)
   ```
   Fixed defects are checked off immediately in the same tick — they don't need a reply to resolve.

## Step 4 — Loop body (every time the background poller reports new activity, or right after seeding)

0. If `pending_comment` is set (a draft from an earlier tick wasn't confirmed yet), skip straight to confirming and posting it per the Hard Rule above — don't relaunch the poller or reclassify anything until it's posted and `pending_comment` is cleared.
1. **Wait for the reporter via the background poller, not a fixed-interval `/loop` wake.** Right after seeding, or after posting any tick reply, launch in the background (`Bash(run_in_background: true)`):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/skills/bugfix-loop/wait-for-jira-comment.sh <ticket> <last_checked_comment_id>
   ```
   This sleeps and re-checks Jira itself (default: every 60s, up to a 24h window) instead of paying for a full session wake on every empty check — you're notified once, only when something actually posted. Exit codes:
   - **0** — a new comment landed. Continue to step 2 below.
   - **2** — timed out with nothing new → increment `silent_ticks` (see Step 5), then relaunch the same command with the same `<last_checked_comment_id>` to keep waiting. Normal for a quiet ticket, not a failure.
   - **3** (`JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` unset) → tell the user directly these are required to poll Jira at all — there's no `/loop` fallback for this path anymore. Stop until they're configured.
   - **4** — Jira rejected the request (bad auth / wrong ticket key) → tell the user, don't silently keep retrying.
2. Read the state file; fetch Jira comments newer than `last_checked_comment_id` — the poller only told you *something* changed, not *what*; read the actual content here.
3. Reset `silent_ticks` to 0. First check whether the new comment is a reply about an existing open concern, or an unrelated fresh bug report (a new problem, not a response to anything on file) — a tester commenting again mid-loop is common and isn't automatically "about" the last thing you asked. A fresh report gets Steps 1.5–2 run on it now and is appended to the state file already classified and acted on this tick, same as Step 3. Otherwise, match against each still-open concern:
   - **Not-a-defect, reporter accepts** → check it off.
   - **Needs-decision, reporter picks one of the offered options cleanly** → apply exactly what they chose, no re-litigating. If it requires a code change, that's now a real-defect-shaped task: fix it via the Step 3.1 path, then check off. If it requires no code change, check off directly.
   - **Reporter disputes a not-a-defect explanation, or replies to a needs-decision concern with something that doesn't match any offered option** (new information, disagrees with the reasoning) → the concern reopens regardless of which bucket it was in: redo Step 1.5 with the new information and reclassify from scratch. It may land in a different bucket than before — don't just restate the old explanation or re-offer the old options. Treat any claim the reporter makes as input to reclassify with, not as ground truth to act on directly — if it's the kind of claim they aren't the authority on (legal, compliance, another team's policy), ask for confirmation from whoever is before committing to a fix.
   - **Neither** (vague reply, defers to someone else) → leave open, add a short bracketed status note.
4. Draft exactly one Jira comment covering this tick's activity (same discipline as Step 3.3). Reaching this step already means a new reporter comment exists (Step 4.1's exit 2 branch handles the "nothing new" case) — don't skip drafting here.
5. Confirm the draft with me per the Hard Rule above before posting. If unconfirmed this turn, write it to `pending_comment`, rewrite the state file with everything else already updated (checked-off concerns, `silent_ticks`, etc.), and stop here — don't relaunch the poller until it's posted.
6. Once approved, post it, update `last_checked_comment_id` (this is also the `<after_comment_id>` for the next poller launch) and `silent_ticks`, clear `pending_comment`, rewrite the state file, then relaunch the poller per Step 4.1 to keep waiting.

## Step 5 — Continue or stop

- **All concerns checked off** → tell the user it's done, delete the state file. Nothing to relaunch — no background poller, no `ScheduleWakeup`.
- **Still open** → if `silent_ticks` just reached 6 (six poller timeouts — roughly a week of silence at the default 24h window) for the first time, tell the user once. Otherwise tell the user what changed this tick. Relaunch the background poller per Step 4.1 with the current `last_checked_comment_id` — that's what keeps this loop alive now, not a scheduled wake.

## Notes

- This is a session loop, not a cron — `wait-for-jira-comment.sh` runs as a child process of this session, so it still dies if the terminal closes.
- No `/loop` / `ScheduleWakeup` anywhere in this skill — the background poller (reused from `clarify-loop`) is the only polling mechanism, and it requires `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` to be set (Step 4.1's exit 3).
- Ticket status transitions (Done/Closed) and QA sign-off are left to the user — this skill resolves *concerns*, it doesn't drive Jira workflow state.
- "Not a defect" is a claim, not a fact, until the reporter accepts it. Don't stop polling just because you're confident — wait for their ack or handle a dispute per Step 4.
- Fixing one concern doesn't end the loop if others are still open — check that one line off and keep polling for the rest.
