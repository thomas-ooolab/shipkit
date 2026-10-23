# /pr — the "Decisions made" block of every PR description

> Loaded by `/pr` Step 5 and 6 (when a PR description is written) and by `review-loop.md` before every `full review` trigger.

**Why.** The review bot takes only the PR links from a Slack trigger and ignores every word around them (AR-583 round 6: the trigger
listed the items already answered, and the bot still raised the same race dispute for the 4th time). What it reads for sure is the
PR description (its own summary is built from it) and the code under review. So what it must not ask again lives in the description.

**The block.** Between two marker lines, in the description of **every** PR of the ticket — each child PR and the root PR:
```
<!-- shipkit:decisions:start -->
## Decisions made
- KD-1 — <one sentence of why> — <test name | file:line>
- OQ-2 — <the choice made and why> — <where it shows: test | file:line | spec section>
- A-3 — not an issue: <one sentence of why> — <test name | file:line>
<!-- shipkit:decisions:end -->
```
Codes: `KD-n` a *Key decision* of `spec.md` (numbered in order), `OQ-n` an open question the PO resolved (`specs/NNN-slug/open-question.md`),
`A-n` an entry of `## Answered findings` in `.shipkit/pr-<ticket>.md` whose status is `not-an-issue`, `pre-existing` or `follow-up` (a
`fixed` one is visible in the code, so it is left out). An item escalated to Jira and still unanswered is written `awaiting PO — <Jira
comment permalink>`. No decision yet → the block is still written, with `- none yet`. `A-n` is numbered consecutively among the lines written, in ledger order. Every line has a code, a one-sentence reason and
where the proof is — a test name or a `file:line` (for a follow-up, the line it concerns); a line with no proof is not written.

**Writing it.** Step 5 and Step 6 put the block at the end of the description they build. After that, `review-loop.md` refreshes it before
every trigger (the seed ping included). Per PR, with `bitbucket-api.sh` (credentials: README → *Bitbucket credentials*):
1. `GET /repositories/<workspace>/<repo>/pullrequests/<id>` → keep `title` and `description`.
2. New description = the text before the start marker + the freshly built block + the text after the end marker; no markers yet → the old
   description, a blank line, then the block. **Everything outside the two markers is kept exactly as it is.** The new block equals the old
   one → no write.
3. Write the body to a file with `{"title": <the current title>, "description": <new description>}` (never through `echo`) and
   `PUT /repositories/<workspace>/<repo>/pullrequests/<id> <body file>`.
4. `GET` again and confirm: both markers present, the text outside them unchanged, `title`, destination branch and reviewers unchanged.
   Any mismatch → say so, do not trigger the bot.

**Only inside `/pr`.** This skill edits a public PR description in its own flow (Phase 1 when it opens the PRs, Phase 2 before each trigger)
and nowhere else; no other skill touches a PR description.
