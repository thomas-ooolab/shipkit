---
name: bugfix
description: "Use when a tester/QA posts a Jira comment reporting a bug on an in-flight feature ticket (the comment is the bug report; on a stand-alone Bug ticket, its own description is) and it needs triage — real defect, expected behavior, product decision, or a defect in someone else's change — and tracking until every reported concern is resolved. Trigger: /bugfix <ticket-id> [<comment-id>] [--agent kiro]. Examples: \"/bugfix AR-460\", \"QA left a bug comment on AR-460, triage it and keep checking until they confirm\""
argument-hint: "<jira-ticket> [<comment-id>] [--agent kiro]"
---

# Bugfix Loop

<!-- report-style:v1 -->
> **Report style.** While this skill runs, the words sent to the user are only: (a) the result, in this skill's own report template; (b) anything done differently from the skill, with the reason; (c) what is blocked, or a decision only the user can make; (d) what the skill cannot know — an error, a measurement, a risk. Do not list the steps you are about to do that the skill already defines, do not repeat the skill's gates or rules — a gate that passed is silent (no "sign-off confirmed", "no conflict", "all checks passed" line), only a gate that failed is reported — do not summarise what you just said. A background wait is one line. No closing menu of "you decide" unless there is a real decision. The skill's report template is the whole report: no extra "Next" or "what's next" paragraph the template does not have.

Investigate a reported bug, fix what's actually broken, explain what isn't, ask about what's genuinely unclear — then keep checking Jira until every concern the reporter raised is resolved, not just replied to once.

Composes existing pieces — do not reimplement any of them:
- **REQUIRED:** `superpowers:systematic-debugging` — trace each reported symptom to root cause before classifying it. Never classify from the ticket text alone.
- **REQUIRED for any code fix:** `superpowers:test-driven-development` — write the regression test first.
- This project's own bugfix mechanics, if it has one (e.g. a `report-bug` skill's dev flow — branch, fix, test, push, PR) — reuse its conventions, don't invent a parallel one. If none exists, just follow the repo's normal branch/commit/PR workflow.
- `clarify`'s state-file/`silent_ticks` shape and business-language rule below — same mechanics, applied to bug concerns instead of spec open-questions.
- **REQUIRED:** `wait-for-jira-comment.sh` (shared at `${CLAUDE_PLUGIN_ROOT}/scripts/` — one script, one source of truth, don't fork it into a bugfix-specific variant). It's a plain interval poller against the Jira REST API (no Slack bot involved), so it fits this skill exactly as-is: pass the ticket and `last_checked_comment_id`, it blocks until a new comment lands. No `/loop`/`ScheduleWakeup` anywhere in this skill — `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` are hard requirements, same as `clarify`.

State lives in `.shipkit/bugfix-<ticket>.md`.

## Hard rules: business language, sound like a person, confirm before every Jira post

**REQUIRED:** Read `${CLAUDE_PLUGIN_ROOT}/references/jira-comment-rules.md` and follow all three rules — here "item" = a
reported concern. They apply to the first comment and every per-tick comment, status notes and acknowledgments included. A
`pending_comment` concern is not checked off until its comment has actually posted.

**REQUIRED:** every write to Slack or Jira goes through the plugin's scripts, never an MCP write tool: `${CLAUDE_PLUGIN_ROOT}/references/write-through-scripts.md`.

Business-language example for this skill — Bad: "`CanViewCallReview` gates on `c.RecordedAt.After(m.AssignedAt)`, so this is by design." Good: "That's how it's built today — a manager only sees calls recorded after they joined the team, not the team's full history before that. Wanted to check: should managers see everything the team ever recorded, or only what happened since they joined?"

One more excuse that belongs to this skill:

| Excuse | Reality |
|---|---|
| "The state file doesn't exist, so this bug report hasn't been triaged yet" | The file's absence proves nothing — check the ticket's comments after the bug report first (Step 1.4). A missing file plus an existing response means resume, not re-triage. |

## Dynamic context (injected)
```
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" resolve`
```

## Step 1 — Resolve inputs & investigate

0. **Bootstrap is a precondition, not a step of this skill.** A new worktree gets `/bootstrap` automatically when
   it is created, so this normally just passes. If `SHIPKIT_CONFIG_EXISTS=0` anyway (worktree made by hand,
   config removed), stop: "Run `/bootstrap` first." — don't guess the submodules, branch names or Jira config:
   `probe.sh state/branch`, `/assign` and `/verify` all read `.shipkit/config.yml`.
1. Ticket ID from args (strip `--agent kiro` first — it only changes *who writes the fix*, Step 3.1). If missing, recommend candidates instead of asking blank: check `.shipkit/bugfix-*.md` for existing state files (in-progress `/bugfix` runs from an earlier session — list any found, most recently modified first) and infer from the current branch name (`feat/AR-{num}-{slug}`) like `/pr` Step 1 does. Exactly one candidate → confirm it with me in one line. More than one, or a state file and branch disagree → ask via `AskUserQuestion` listing each. Neither → ask for the ticket ID plainly. Normally the ticket is an existing feature ticket already being built — the bug report is a **comment** on it, not the ticket's own description (that's the feature spec, unrelated to what's being triaged here). **Exception: a stand-alone bug ticket** (Jira issue type `Bug`, read with `getJiraIssue`) — there the **description is the bug report** (Step 1.2).
2. Find the comment(s) to triage: if the invocation points at a specific comment, use that. On a stand-alone bug ticket with no comment named, the **description** is the report (`seed_comment_id: description`); later comments come in through Step 4.3 like any new comment. Otherwise take the latest tester/QA comment that reports unexpected behavior (skip status updates, unrelated remarks) — if more than one recent comment could qualify, ask the user which one. If it lists multiple distinct problems (e.g. a numbered list), treat each as a separate concern.
3. The person to reply to is the **author of that comment** — not the ticket's Jira "Reporter" field, which is usually whoever filed the original feature ticket, not the tester who found the bug. For a description report the person is the ticket's reporter (`reporter.accountId`), who is also the PO here unless you are told otherwise: tag them once. If the comment author is ambiguous (shared/bot account), ask the user once and remember for this ticket only.
4. **Before triaging, check whether this exact bug report already has a response.** The local state file is not the source of truth for "already triaged" — the ticket's comments are. The file can be missing for reasons unrelated to whether a response exists: a fresh clone/worktree, a teammate ran this from another machine, or the response posted but the file write never happened. Fetch the ticket's comments posted *after* the bug-report comment found in step 2 (a description report: every comment on the ticket) and look for one from you/the bot account that already addresses it (a fixed-and-pushed note, a not-a-defect explanation, or lettered options, in this skill's own comment style — see Steps 2–3).
   - **Found one** → treat it as the already-posted tick response. Reconstruct `.shipkit/bugfix-<ticket>.md` from it: `commenter_account_id`, `reporter_account_id`, `seed_comment_id` (the bug-report comment), `last_checked_comment_id` set to that response comment's ID, `pending_comment: null`, `silent_ticks: 0`, and the concerns checklist with each concern's status as that comment states it. Do not re-run systematic-debugging and do not draft a new comment. Skip the rest of Step 1 and Steps 2–3 entirely — go straight to Step 4's loop body.
   - **Nothing found** → this is a genuine first triage, continue below.
5. Separately, identify the **PO** — the person who actually owns the business call on this feature. Check the ticket's reporter field first (on a feature ticket it's usually the PO); if that's wrong for this project (bot, or someone else owns product calls here), ask the user once and remember for this ticket only. You'll @-mention the PO whenever a concern needs their ruling (Step 3.3) — the tester gets acknowledged either way, but they aren't who decides.
6. Invoke `superpowers:systematic-debugging` on each concern, reading the real code path — not just reasoning from the comment's description of symptoms.
7. **Find the change that introduced it, and who owns it.** For each concern's faulty lines (`file:line` from 1.6), inside the affected
   submodule (the repo root on a single-repo topology), against the tracking branch: `git blame -L <start>,<end> --date=short origin/<target> -- <file>`
   and `git log -L<start>,<end>:<file> origin/<target> -s --format='%h %ad %an | %s'`. Take the **most recent** commit that changed those
   lines; skip a bulk-import / "Move to new repo" commit when a later one exists. Only the import commit touches them →
   `pre-existing, no owning ticket`: nobody to hand off to, continue as today. A commit on this ticket's own unmerged branch
   (`git log origin/<target>..HEAD` touches the lines) is this ticket's own change → mine.
   From the commit read the sha, date, author name and email (add `%ae` to the format) and the ticket key (the commit subject, else the
   branch it merged from, else its PR). **Owner = the commit author, resolved to a Jira user**: look the email, then the name, up with
   `lookupJiraAccountId` (e.g. `Jane Doe <jane@example.com>` → Jira `Jane Doe`) and keep the `accountId`. Only when the author cannot be
   matched, read the introducing ticket (`getJiraIssue`: assignee and status) and use its assignee — never an assignee who is the tester
   (the ticket is in a testing status such as Testing or QA: they test the change, they did not write it). The author is an agent or
   bot (Claude, kiro, a noreply address) or appears only in a `Co-Authored-By` trailer, or no usable assignee is left → `AskUserQuestion`,
   never assume. **Is the user the owner?** Compare the owner's `accountId` with the current user's Jira account (`atlassianUserInfo`);
   the same ticket as the one being fixed counts as yes. Keep per concern: `introduced by <ticket> <sha> (<author>, <date>) · owner <name> · <mine | handed off>`.

## Step 2 — Classify each concern into exactly one bucket

**Gate first — a precondition, not a judgment.** Every tester/QC comment this tick triages (the comment(s) of Step 1.2, or `description` for a description report, and each
new comment in Step 4.3) needs one of these before a bucket is chosen, and again before Step 3.5 / 4.6 posts:
- `.shipkit/evidence/<TICKET>/cross-check-post.md` exists and its `Comments:` line names that comment's id; or
- the state file carries `gate: skipped <comment-id> - <one-line reason: the comment reports a malfunction (crash, wrong total,
  broken layout) or a plain reply, and states no claim of kind (a), (b) or (c)>`. On the first tick, before Step 3.5 has written
  the state file, create `.shipkit/bugfix-<ticket>.md` holding just the `gate:` lines; Step 3.5 keeps them.

Neither → run `/cross-check <TICKET> --stage post <comment-id>…` (every id that has neither) before choosing a bucket. Kinds
(a), (b), (c) are the claim kinds in `${CLAUDE_PLUGIN_ROOT}/skills/cross-check/SKILL.md`, *Step 2 — Select claims*; read them
there, they are not restated here. The comment alone proves neither that the code is wrong nor that the spec is. Then: verdict
`fix first` → Real defect; `ask PO` or any `[ticket-conflict]` → Needs a product decision (its draft PO question goes through
the confirm-before-post rule above; `/cross-check` itself posts nothing); a later dated decision that backs the code → Not a
defect, citing that comment. Cross-check is not run just because a fix was implemented.

- **Real defect** — the code contradicts its own stated/implied intent, or produces an outcome nothing about the design supports → fix it. No explanatory comment for this concern (Step 3 posts a status note instead, not a "why").
- **Not a defect** — the code does exactly what it was deliberately built to do, and the reasoning holds up → business-language comment explaining why.
- **Needs a product decision** — the behavior could be intentional or wrong depending on unstated business intent, or multiple valid fixes exist and choosing between them is a product call → business-language comment with lettered options.

- **Owned by someone else** — a concern that would be a Real defect, but Step 1.7 found its introducing change belongs to another person's ticket → **no code change, no branch, no `/assign`, no kiro, no `/verify`.** Draft a short hand-off message for that owner instead (a dev, so technical is fine, unlike the tester/PO comment rules): the symptom and repro, the root cause with `file:line`, the introducing commit + ticket + date, the evidence that confirms it (the query, log or test output you actually ran), and the suggested fix as a proposal. Tag the owner as `@[Name](accountId)` (the `accountId` from `lookupJiraAccountId`) and name the introducing ticket in the text. Show it to me with this tick's comment draft per the confirm-before-post rule above; by default it posts as its own Jira comment on **this bug ticket** (`jira-comment.py`, so the mention notifies the owner), and I can pick another place: a Slack message, a comment on the introducing ticket, or copied by hand.

A ticket can have concerns in different buckets at once — classify each on its own merits. A mixed ticket fixes the user's own concerns and hands off the rest in the same tick.

## Step 3 — Act, then post ONE Jira comment for the tick

0. **Tell me what each bug is, then fix what nothing blocks.** For every real-defect concern — including one a PO's choice (Step 4.3) turned into a code change — print this block, in my language, before the first edit, test, branch, `spec.md` task or `/assign` brief (`--agent kiro` too), all concerns in one message. Every field is filled from Step 1.6–1.7, none is "TBD":
   ```
   🐞 <TICKET> · <concern, in the tester's words>
      What happens:  <the symptom, and the steps that show it>
      Root cause:    <file:line — what the code does, against what it should do>
      Introduced by: <ticket> <sha> (<author>, <date>) | pre-existing, no owning ticket
      Fix:           <the change, one line> · regression test: <what it asserts>
      Status:        fixing now | held: <blocker> — <what I need from you>
   ```
   `Status` is `fixing now` unless one of these holds (*Owned by someone else* is Step 2's bucket, with its own hand-off):
   - **Not this ticket's** — the faulty lines predate it (`pre-existing, no owning ticket`) and no `REQ-NNN`, task or file of this ticket's branch (`git diff origin/<target>...HEAD --name-only`) covers the broken behaviour.
   - **Against the spec** — the fix would change a `REQ-NNN`, `## Contracts` entry or `## Plan` decision that no cited decision backs (Step 3.1b).
   - **Not enough to fix on** — no reproduction, no `file:line` root cause, more than one valid fix (a product call), or the fix needs a migration / backfill of existing data.
   - **Anything else** that would make writing the fix a guess: name it.

   Nothing blocks → no wait: go straight on to 1. A held concern gets no branch, test, task, brief or edit, and no line in this tick's Jira comment; it stays open in the state file. Fix every other concern now (1) — never hold them back for the held ones. Once this tick's fixes are done, ask me about the held ones (`AskUserQuestion`, one question each, the blocker as options) in the same turn as the draft's confirmation (3.4). When I answer, run `/cross-check <TICKET> --stage post <comment-id>` again on that concern with my answer as a new fact — the Step 2 gate file is rewritten, not skipped — then classify it again and run this step on it again.
1. Fix every concern whose `Status` is `fixing now` (not the *Owned by someone else* ones: no branch, no fix, no `/assign`), on the ticket's **existing unmerged branch** — `feat/…`, or the `fix/…` of an earlier fix (first apply `/assign` Step 4b to it — merged, behind the target, overlapping — before any fix is written or handed out) — a bug reported on an in-flight feature ticket almost always has one already; find it with `probe.sh state <TICKET>` and check it out. Pushing there auto-updates any open PRs. No unmerged branch yet (none, or the feature's code already merged) → create it from the submodule's tracking `branch` under exactly the name `probe.sh branch <TICKET> <submodule|parent> --fix` prints (`fix/<ticket>-<slug><suffix>`; the parent already sits on `fix/<ticket>-*` when `/developer` made the worktree) — never `hotfix/…`, an agent's or another flow's own naming. Regression test first.
   **`--agent kiro`: claude coordinates, a kiro worker writes the fix.** Per real-defect concern, append fix tasks to the ticket's
   `spec.md` `## Tasks` (`- [ ] T0NN [REQ-NNN] (<submodule>) {fix, regression test first} — <file path>`, REQ = the
   requirement whose behavior is broken), then run `/assign <TICKET> --only <submodules> --agent kiro --no-push` and wait for its
   report: it opens a kiro terminal per submodule, which commits to the feature branch and never pushes (`--no-push` keeps
   `/assign` from pushing too) — so the fix is verified before anything leaves the machine; a `FAILED` verify means new
   tasks and another `/assign`, never a claim in Jira. If `/assign`
   asks about a submodule already in progress, that is the user's answer, not yours. `/assign` runs in Orca mode when this session is in an Orca worktree: its report must show `transport: orca (worktree <id>)`, and a `transport: agent` there is a deviation to stop on, not to accept — never the `Agent` tool as a fallback.
   **`probe.sh state` gives `SPEC=none`** (a stand-alone bug ticket: the bug report is the ticket description, there is no feature
   spec, and `/run-pipeline --bug` never creates one) **→ run `/assign` in free-form mode instead of stopping.** Per real-defect
   concern, `cd` into the affected submodule (the repo root on a single-repo topology), run
   `/assign "<brief>" --agent kiro --no-push` there, then `cd` back: free-form mode takes the repo `git rev-parse --show-toplevel`
   prints as its one target, and `--worktree current` still resolves to this worktree from inside a submodule. The brief carries the
   concern in the tester's words, the root cause `superpowers:systematic-debugging` found (`file:line`), the branch name
   `probe.sh branch <TICKET> <submodule|parent> --fix` prints (create it from the tracking branch if missing, else continue on it),
   "regression test first", and "run the tests of the files you changed (`${CLAUDE_PLUGIN_ROOT}/references/scoped-tests.md`, never the whole suite), commit, never push". No `spec.md` is created or edited. Everything else in
   this step stays: kiro writes the fix, `/verify --concern` proves it before any push, a `FAILED` verify means a new brief and
   another `/assign`.
   `/assign` stops for any other reason → **stop and tell the user why** (one line, in the user's language); never fall back to
   fixing inline — the flag means kiro writes the fix, and an inline fix by claude is not what was asked. Inline is only
   for a run without `--agent kiro`.
   **1b. Keep `spec.md` true.** `SPEC=none` → nothing to keep true: skip this step (`/run-pipeline --bug` reads that as "spec unchanged"). After the fix, compare what the code now does with the ticket's spec (`probe.sh state` → `SPEC`):
   a `REQ-NNN`, a `## Contracts` entry or a `## Plan` decision that no longer matches is edited **in place** (the fix tasks stay in `## Tasks`; no
   new spec, no `/plan-deep`, no `/clarify`). Every such edit needs a source — the PO's chosen option or a dated Jira decision, cited by comment id in
   the tick comment; an edit nobody decided is a Needs-a-product-decision concern, not a fix. The code was wrong and the spec was right → the spec is
   not touched. `/run-pipeline --bug` reads the result from `git diff` of `spec.md` outside `## Tasks` and, when it changed, runs a stand-alone
   `/verify --ticket <t> --req <the REQs the edit touched>` after this skill; run on its own, say in the tick comment that the spec changed.
   **Then prove it with `/verify`** — a passing unit test is not a pass. After the **last** code change of the tick, run `/verify --ticket <TICKET> --concern "<the reported scenario, in the tester's words>"` once per real-defect concern (repeat `--concern`). `/verify` owns the proof: it drives the steps on the running app, saves the evidence under `.shipkit/evidence/<TICKET>/`, shows it, emits `verify: PASS | FAILED | INCOMPLETE` and writes the evidence table to `.shipkit/evidence/<TICKET>/jira-comment-<date-time>.md` (its newest file; the format is `/verify`'s `evidence-table.md`, FE proof embedded as the screenshot). It posts nothing; this skill's own tick comment (3.3) carries the table.
   **Any agent you brief to drive a browser** (a worker writing its own Playwright script, or one running `/verify`) gets the *Browser rules* of
   `${CLAUDE_PLUGIN_ROOT}/references/browser-agents.md` in its brief, and when it ends or is stopped you run
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-browsers.sh" <its scratch directory>` (stopping an agent does not stop its browsers).
   **A concern is `fixed` only when `/verify` returns PASS for it and its evidence file exists.** `FAILED` → keep fixing; `INCOMPLETE` → don't draft the Jira comment yet: resolve it as `/verify` says ("Building a variant"), and ask me only for what you can't create yourself. Not proven yet = not passed: don't push-and-announce it, don't check it off, don't claim it in the Jira comment. Push only after PASS (`--agent kiro`: the commits are local until you push them after PASS).
3. Draft exactly one Jira comment covering every concern from this tick except the held ones (3.0): a factual fixed-and-pushed note per defect (link the branch/PR; say in plain words that you re-checked it yourself in the app, and show the proof the tester can read: paste the rows of the newest `.shipkit/evidence/<TICKET>/jira-comment-*.md` for the fixed defects as they are, images included — its format is `/verify`'s, never retyped or reworded here. Never claim "verified" for a fix you only unit-tested), the business-language explanation per not-a-defect concern, the lettered options per needs-decision concern. A question that has an `OQ-N` in `open-question.md` is labelled with it (`OQ-3. …`; merged from several: `OQ-3 / OQ-19. …`), never numbered by hand. One comment, not one per concern. Tag the **tester** throughout (they reported it, they get the update either way) as `@[Name](commenter_account_id)`; additionally @-mention the **PO** as `@[Name](reporter_account_id)` on any not-a-defect or needs-decision concern — that's their ruling to make or confirm, not the tester's. Real-defect status notes don't need the PO tagged. When the tester and the PO are the same account (a description report), tag them once. Apply *Claims about today's behaviour and the scope of proposals* (`${CLAUDE_PLUGIN_ROOT}/references/jira-comment-rules.md`) to every statement of what the product does today, the not-a-defect explanation included, and to every lettered option that names a scope. An *Owned by someone else* concern gets one plain sentence in the tester's comment (it belongs to another change and is being passed to its owner; no names beyond the ticket key); its hand-off message is shown with the draft and, once confirmed, posts as its own comment on this ticket (Step 2), not inside this one.
4. Save the draft as `.shipkit/bugfix-<ticket>-draft.md` (never the scratchpad or `/tmp`: `jira-comment-rules.md`, *Where the draft lives*), then confirm it with me per the Hard Rule above before posting, with its Claims list and every `gate: skipped` line of this tick next to it. If unconfirmed this turn, set `pending_comment` to that path in the state file below and stop — don't launch the background poller yet.
5. Once approved, check the Step 2 gate once more for every comment id this draft answers, then post it with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" post <TICKET> --file .shipkit/bugfix-<ticket>-draft.md` (the MCP tool leaves mentions as plain text; If `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` are unset (script exits 3), fall back to `addCommentToJiraIssue` and warn the user that mentions will NOT notify anyone. Exit 5 = posted but a mention didn't land — tell the user (the comment id is still printed). The script reads the comment back and prints `"images": {"in_table": n, "outside_table": m}` — `outside_table` must be `0` and `in_table` the FE screenshots you embedded, else say so. Read the comment back to check the numbers of any plain numbered list (`${CLAUDE_PLUGIN_ROOT}/references/jira-comment-rules.md`, *Numbering*). Approved text stays approved when only the layout changes; changed wording is shown again first.), then write `.shipkit/bugfix-<ticket>.md`:
   ```markdown
   # Bugfix loop state — <ticket>
   commenter_account_id: <id of the tester/QA who posted the bug comment — the ticket's reporter for a description report>
   reporter_account_id: <the PO's id — the spec's reporter_account_id, else the ticket's reporter field>
   seed_comment_id: <id of the comment being triaged, or `description`>
   last_checked_comment_id: <id>
   silent_ticks: 0
   pending_comment: null   # or .shipkit/bugfix-<ticket>-draft.md while a draft waits for approval

   ## Concerns
   - [x] <defect concern text> — fixed, <branch/PR link>, verified: <`/verify` PASS — FE browser | BE request | both>, evidence: <path(s) under .shipkit/evidence/<TICKET>/>
   - [ ] <not-a-defect concern text> (awaiting reporter ack)
   - [ ] <needs-decision concern text> (awaiting reporter's choice: A/B/...)
   - [ ] <owned-elsewhere concern text> — owner: <name>, <ticket>, <sha>, handed off
   - [ ] <held concern text> — held: <blocker>, awaiting dev's answer
   ```
   Step 2's gate may add `gate: skipped <comment-id> - <reason>` lines (one per comment) above `## Concerns`; rewriting the file keeps them.
   An *Owned by someone else* line is checked off only when I say the owner fixed it, or it is dropped; until then the concern stays open and the loop keeps polling.
   A fixed defect needs no reply from the reporter, but **check it off (`[x]`) only once the Jira comment that reports it has actually posted** (Step 3.5 succeeded). While that comment is still a `pending_comment` draft, keep the line `[ ]` and add `— fixed + verified, comment awaiting approval`; flip it to `[x]` right after the post. (Step 5's summary still shows it ✅ as soon as its evidence file exists — the checkbox tracks "reported to the tester", the summary tracks "fixed and proven".)

## Step 4 — Loop body (every time the background poller reports new activity, or right after seeding)

0. If `pending_comment` is set (a draft from an earlier tick wasn't confirmed yet), skip straight to confirming and posting it per the Hard Rule above — don't relaunch the poller or reclassify anything until it's posted and `pending_comment` is cleared.
1. **Wait for the reporter via the background poller, not a fixed-interval `/loop` wake.** Right after seeding, or after posting any tick reply, launch in the background (`Bash(run_in_background: true)`):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/wait-for-jira-comment.sh <ticket> <last_checked_comment_id>
   ```
   This sleeps and re-checks Jira itself (default: every 60s, up to a 24h window) instead of paying for a full session wake on every empty check — you're notified once, only when something actually posted. Exit codes:
   - **0** — a new comment landed. Continue to step 2 below.
   - **2** — timed out with nothing new → increment `silent_ticks` (see Step 5), then relaunch the same command with the same `<last_checked_comment_id>` to keep waiting. Normal for a quiet ticket, not a failure.
   - **3** (`JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` unset) → tell the user directly these are required to poll Jira at all — there's no `/loop` fallback for this path anymore. Stop until they're configured.
   - **4** — Jira rejected the request (bad auth / wrong ticket key) → tell the user, don't silently keep retrying.
2. Read the state file; fetch Jira comments newer than `last_checked_comment_id` — the poller only told you *something* changed, not *what*; read the actual content here.
3. Reset `silent_ticks` to 0. The Step 2 gate must hold for every new comment id before you match it. First check whether the new comment is a reply about an existing open concern, or an unrelated fresh bug report (a new problem, not a response to anything on file) — a tester commenting again mid-loop is common and isn't automatically "about" the last thing you asked. A fresh report gets Steps 1.5–2 run on it now and is appended to the state file already classified and acted on this tick, same as Step 3. Otherwise, match against each still-open concern:
   - **Not-a-defect, reporter accepts** → check it off.
   - **Needs-decision, reporter picks one of the offered options cleanly** → apply exactly what they chose, no re-litigating. If it requires a code change, that's now a real-defect-shaped task: fix it via the Step 3.0–3.1 path (report first), then check off. If it requires no code change, check off directly.
   - **Reporter disputes a not-a-defect explanation, or replies to a needs-decision concern with something that doesn't match any offered option** (new information, disagrees with the reasoning) → the concern reopens regardless of which bucket it was in: redo Step 1.5 with the new information and reclassify from scratch. It may land in a different bucket than before — don't just restate the old explanation or re-offer the old options. Treat any claim the reporter makes as input to reclassify with, not as ground truth to act on directly — if it's the kind of claim they aren't the authority on (legal, compliance, another team's policy), ask for confirmation from whoever is before committing to a fix.
   - **Held (Step 3.0)** → stays open whatever the reporter says; it leaves `held` only when I answer.
   - **Owned by someone else** → stays open whatever the reporter says; check it off only when I say the owner fixed it, or it is dropped.
   - **Neither** (vague reply, defers to someone else) → leave open, add a short bracketed status note.
4. Draft exactly one Jira comment covering this tick's activity (same discipline as Step 3.3). Reaching this step already means a new reporter comment exists (Step 4.1's exit 2 branch handles the "nothing new" case) — don't skip drafting here.
5. Save the draft as `.shipkit/bugfix-<ticket>-draft.md` (overwriting the last tick's), then confirm it with me per the Hard Rule above before posting, with its Claims list and every `gate: skipped` line of this tick next to it. If unconfirmed this turn, set `pending_comment` to that path, rewrite the state file with everything else already updated (checked-off concerns — not the ones this unposted draft reports —, `silent_ticks`, etc.), and stop here — don't relaunch the poller until it's posted.
6. Once approved, post it via the script (Step 3.5, gate re-check included), update `last_checked_comment_id` (this is also the `<after_comment_id>` for the next poller launch) and `silent_ticks`, clear `pending_comment`, rewrite the state file, then relaunch the poller per Step 4.1 to keep waiting.

## Step 5 — Continue or stop

- **Every time Step 5 runs (done or still open), first print the summary from the state file — and show the evidence, not just claim it:**
  ```
  shipkit · bugfix <TICKET> — <n> concern(s)
  ✅ Fixed:        <concern> — <branch/PR> · evidence: <screenshot .png | request+response/data .txt> (<path>)
  💬 Not a defect: <concern> — <reporter accepted | awaiting ack>
  ❓ PO decision:  <concern> — <Jira comment permalink>
  🔧 Not fixed:    <concern> — <why: unverified | blocked | held: <blocker> | waiting on reporter>
  🤝 Handed off:   <concern> — owner <name>, <ticket> <sha>, <where the hand-off went>
  ```
  Under it, one line per concern, fixed or not: `introduced by <ticket> <sha> (<author>, <date>) · owner <name> · <mine | handed off>` (`pre-existing, no owning ticket` when Step 1.7 found none).
  A concern is listed ✅ only when its evidence file exists; otherwise it is 🔧. The evidence itself was shown by `/verify`; list its paths.
- **All concerns checked off** → tell the user it's done, delete the state file (leave `.shipkit/evidence/<TICKET>/` in place). Nothing to relaunch — no background poller, no `ScheduleWakeup`.
- **Still open** → if `silent_ticks` just reached 6 (six poller timeouts — roughly a week of silence at the default 24h window) for the first time, tell the user once. Otherwise tell the user what changed this tick. Relaunch the background poller per Step 4.1 with the current `last_checked_comment_id` — that's what keeps this loop alive now, not a scheduled wake.

## Notes

- This is a session loop, not a cron — `wait-for-jira-comment.sh` runs as a child process of this session, so it still dies if the terminal closes.
- No `/loop` / `ScheduleWakeup` anywhere in this skill — the background poller (reused from `clarify`) is the only polling mechanism, and it requires `JIRA_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` to be set (Step 4.1's exit 3).
- Ticket status transitions (Done/Closed) and QA sign-off are left to the user — this skill resolves *concerns*, it doesn't drive Jira workflow state.
- "Not a defect" is a claim, not a fact, until the reporter accepts it. Don't stop polling just because you're confident — wait for their ack or handle a dispute per Step 4.
- Fixing one concern doesn't end the loop if others are still open — check that one line off and keep polling for the rest.
