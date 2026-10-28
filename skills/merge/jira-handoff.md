# /merge — Step 10: move the Jira ticket

> Loaded by SKILL.md after every PR of the ticket is merged. `JIRA_NOTE` and the history sample are used by Step 11's report.

## Step 10 — Move the Jira ticket
Only when **every** PR of the ticket — all child PRs and the root — is `MERGED` (re-read each PR's
state from Bitbucket; don't trust your own log). Not all merged → don't touch Jira, but still report
it (Step 11). **This step is never skipped silently** — no config value means *decide from history*, and only unusable history means *ask*.
Worktrees are ephemeral, so `.shipkit/config.yml` (gitignored) is not durable: decide from **recent history**, and let
config only override. `jira.after_merge_transition` (a status *name*, never a remembered transition id — ids differ
per project) and `jira.qc_account_id`, when present, win. Otherwise use the *history sample* below.

**History sample (once, shared by 1 and 3).** `atlassianUserInfo` → my `accountId`. `searchJiraIssuesUsingJql`:
`project = <P> AND status CHANGED BY currentUser() ORDER BY updated DESC`, the last ~10 other than `<TICKET>`; read each
issue's changelog (`expand=changelog` via the REST call in 2, or `getJiraIssue`). Per issue, my **latest** status
change is the hand-off after the work was done: record the status it moved to, and — from the `assignee` entry made
by me within two minutes of it — who was assigned. An issue without that data is not a sample for that field.
Take the most frequent value per field. It is **usable** only with at least 3 samples **and** a leader strictly ahead
of the runner-up; the chosen status must also be among this ticket's transitions (`getTransitionsForJiraIssue`, by
name) and the chosen assignee in its assignable users (2). Anything unusable → the question in 1 / 3 with the
top candidates (never more than ~4); never guess.
**Always say what was decided and why**, in `JIRA_NOTE` and the Step 11 line, e.g. `status <name> (n of m),
assignee <displayName> (n of m)` (m = the usable samples for that field) — or `(config)` — so the user can correct it afterwards.
Keep a running `JIRA_NOTE` (what did and didn't happen, and why) for Step 11.
**Always in this order, never asked about: status, then assignee, then the evidence comment.** Once every PR is `MERGED`, run
1 (status) → 2–4 (assignee) → 5 (verify the two) → 6 (evidence) one after the other. Do not ask whether to do any of them, whether
to do them in this order, or for a go-ahead before the comment: the format is agreed and the order is fixed. The only reason to stop
and ask is a **blocker** — a step that cannot be decided or that errors, each named below.
1. **Transition.** `getTransitionsForJiraIssue` for the ticket, and read its current `status.name`.
   - Config value set and found **by name** → `transitionJiraIssue` with that id.
   - Else the history sample is usable → that status, found **by name** among the transitions → `transitionJiraIssue` with its id.
   - Else (no config value, history unusable: fewer than 3 samples, a tie, or the status isn't available on this
     ticket) → **blocker**: `AskUserQuestion` "Move <TICKET> (now: <status.name>) to which status?" with the top history
     candidates that exist among the ticket's real transitions (else the ~4 most relevant transition names; "Other"
     resolves against the list); say why it's asking. Then `transitionJiraIssue` with the pick.
   - `transitionJiraIssue` errors → **blocker**: `JIRA_NOTE` = the error verbatim; do not assign and do not post the evidence
     (the comment is the proof of a status change that did not happen); stop this step and report in Step 11.
2. **Fetch assignable users** for the ticket (the Atlassian MCP has no such lookup —
   `lookupJiraAccountId` is an unfiltered name search — so use REST with the `JIRA_URL`/`JIRA_EMAIL`/
   `JIRA_API_TOKEN` the sibling skills already require):
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" assignable <TICKET>` (prints a JSON array of the active users; Jira writes go through the scripts only: `${CLAUDE_PLUGIN_ROOT}/references/write-through-scripts.md`)
   → keep `accountId`, `displayName` of active users. Creds unset, HTTP error or empty list → do
   **not** guess an assignee: leave it as is, add the reason to `JIRA_NOTE`, go to 5.
3. **Assignee (QC).** `jira.qc_account_id` when set and in the fetched list → that account. Else the history sample is
   usable and its most frequent accountId is in the fetched list → that account. Else (unusable history, or the account
   isn't assignable on this ticket) → `AskUserQuestion` "Who is the QC for <TICKET>?" with options from the fetched list
   only — the top history candidates first, else the ~4 most relevant (e.g. recent reporter/commenters); "Other" resolves against
   the fetched list. Never assign an account absent from it.
4. `editJiraIssue` with `fields: {"assignee": {"accountId": "<chosen accountId>"}}`.
5. Verify from the responses/a fresh `getJiraIssue`: `status.name` and `assignee.accountId` match
   what was requested; report a mismatch as a failure, not a success. Record the final `status.name`
   and assignee for Step 11.
6. **Evidence comment — last, straight after 5, no approval wait.** Run `/verify --ticket <TICKET> --send-evidence` (its Step 7:
   checks the draft is complete against the agreed format and, when it is, posts or edits the one comment).
   - Sent (`evidence comment posted|edited`) → record the permalink for Step 11.
   - The newest draft is a bug fix's table (first header cell `Concern`; verify reports `evidence not sent from here — bug-fix table`)
     → `JIRA_NOTE` = "evidence: bug-fix table, carried by /bugfix's own comment"; not a blocker and not "no draft" — the draft
     exists and verify passed. If `.shipkit/bugfix-<TICKET>.md` still lists that comment as a `pending_comment` (unposted), say so
     and name the draft path, so the user knows it still has to go out.
   - No `.shipkit/evidence/<TICKET>/jira-comment-*.md` draft at all (`--no-jira`, verify not PASS) → `JIRA_NOTE` = "no
     evidence draft"; not a blocker.
   - The draft is **incomplete** (verify reports `evidence NOT sent — incomplete: …`) → **blocker**: the status and assignee are
     already changed, so say what is missing (`JIRA_NOTE` = "evidence NOT sent — incomplete: <what>") and stop; Step 11 names
     the manual step. Don't post a partial table.
   - Its id file exists but the comment was deleted → create it anew without asking; `JIRA_NOTE` = "evidence re-created
     (the earlier comment was deleted)".
   - The send errored (Jira env unset, edit rejected) → **blocker**: `JIRA_NOTE` = the reason; Step 11 says the evidence was
     not sent while the status and assignee were changed.
No Jira comment other than the evidence comment unless the user approves the exact text first.
