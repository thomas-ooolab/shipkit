# /merge — Step 10: move the Jira ticket

> Loaded by SKILL.md after every PR of the ticket is merged. `JIRA_NOTE` and the history sample are used by Step 11's report.

## Step 10 — Move the Jira ticket
Only when **every** PR of the ticket — all child PRs and the root — is `MERGED` (re-read each PR's
state from Bitbucket; don't trust your own log). Not all merged → don't touch Jira, but still report
it (Step 11). **This step is never skipped silently** — no config value means *decide from history*, and only unusable history means *ask*.
Worktrees are ephemeral, so `.shipkit/config.yml` (gitignored) is not durable: decide from **recent history**, and let
config only override. `jira.after_merge_transition` (a status *name*, never a remembered transition id — ids differ
per project) and `jira.qc_account_id`, when present, win. Otherwise use the *history sample* below.

**History sample (once, shared by 10.1 and 10.3).** `atlassianUserInfo` → my `accountId`. `searchJiraIssuesUsingJql`:
`project = <P> AND status CHANGED BY currentUser() ORDER BY updated DESC`, the last ~10 other than `<TICKET>`; read each
issue's changelog (`expand=changelog` via the REST call in 10.2, or `getJiraIssue`). Per issue, my **latest** status
change is the hand-off after the work was done: record the status it moved to, and — from the `assignee` entry made
by me within two minutes of it — who was assigned. An issue without that data is not a sample for that field.
Take the most frequent value per field. It is **usable** only with at least 3 samples **and** a leader strictly ahead
of the runner-up; the chosen status must also be among this ticket's transitions (`getTransitionsForJiraIssue`, by
name) and the chosen assignee in its assignable users (10.2). Anything unusable → the question in 10.1 / 10.3 with the
top candidates (never more than ~4); never guess.
**Always say what was decided and why**, in `JIRA_NOTE` and the Step 11 line, e.g. `status <name> (n of m),
assignee <displayName> (n of m)` (m = the usable samples for that field) — or `(config)` — so the user can correct it afterwards.
Keep a running `JIRA_NOTE` (what did and didn't happen, and why) for Step 11.
**Evidence goes out first, and only when a transition will happen.** The `/verify` evidence is sent to the
ticket right before the status changes — never earlier (not after verify, not at `/pr`), never when the user
chose not to transition. Once the target transition is settled (config name found, decided from history, or the user picked one),
and **before** calling `transitionJiraIssue`, run `/verify --ticket <TICKET> --send-evidence` (its Step 7: checks the
draft is complete against the agreed format and, when it is, posts or edits the one comment — no approval wait).
- Sent (`evidence comment posted|edited`) → go on to `transitionJiraIssue`.
- No `.shipkit/evidence/<TICKET>/jira-comment-*.md` draft (bug ticket, `--no-jira`, verify not PASS) → `JIRA_NOTE` = "no
  evidence draft", transition anyway.
- The draft is **incomplete** (verify reports `evidence NOT sent — incomplete: …`) → a problem: `AskUserQuestion`
  naming what is missing, options "skip the evidence and transition anyway" / "stop — don't transition". Skip →
  `JIRA_NOTE` = "evidence skipped: <what was missing>", transition anyway; stop → no transition, Step 11 says why.
- `/verify` asks whether to create the evidence comment anew (its id file exists but the comment was deleted) → the
  user's answer decides: yes → it is sent, then transition; no → `JIRA_NOTE` = "evidence not re-created (comment
  deleted)", transition anyway.
- The send errored (Jira env unset, edit rejected) → **don't transition**; `JIRA_NOTE` = the reason; Step 11 says
  evidence was not sent and the ticket stays where it is.
1. **Transition.** `getTransitionsForJiraIssue` for the ticket, and read its current `status.name`.
   - Config value set and found **by name** → send the evidence (above), then `transitionJiraIssue` with that id.
   - Else the history sample is usable → that status, found **by name** among the transitions → send the evidence,
     then `transitionJiraIssue` with its id.
   - Else (no config value, history unusable: fewer than 3 samples, a tie, or the status isn't available on this
     ticket) → `AskUserQuestion` "Move <TICKET> (now: <status.name>) to which status?" with the top history
     candidates that exist among the ticket's real transitions (else the ~4 most relevant transition names; "Other"
     resolves against the list) **plus** "Don't move the status this time"; say why it's asking. Picked a transition →
     send the evidence, then `transitionJiraIssue`. Picked "Don't move…" → no transition; `JIRA_NOTE` = "user chose not to
     transition". Continue to 10.2 either way.
   - `transitionJiraIssue` errors → `JIRA_NOTE` = the error verbatim; continue to 10.2.
2. **Fetch assignable users** for the ticket (the Atlassian MCP has no such lookup —
   `lookupJiraAccountId` is an unfiltered name search — so use REST with the `JIRA_URL`/`JIRA_EMAIL`/
   `JIRA_API_TOKEN` the sibling skills already require):
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" assignable <TICKET>` (prints a JSON array of the active users; Jira writes go through the scripts only: `${CLAUDE_PLUGIN_ROOT}/references/write-through-scripts.md`)
   → keep `accountId`, `displayName` of active users. Creds unset, HTTP error or empty list → do
   **not** guess an assignee: leave it as is, add the reason to `JIRA_NOTE`, go to 10.5.
3. **Assignee (QC).** `jira.qc_account_id` when set and in the fetched list → that account. Else the history sample is
   usable and its most frequent accountId is in the fetched list → that account. Else (unusable history, or the account
   isn't assignable on this ticket) → `AskUserQuestion` "Who is the QC for <TICKET>?" with options from the fetched list
   only — the top history candidates first, else the ~4 most relevant (e.g. recent reporter/commenters); "Other" resolves against
   the fetched list. Never assign an account absent from it.
4. `editJiraIssue` with `fields: {"assignee": {"accountId": "<chosen accountId>"}}`.
5. Verify from the responses/a fresh `getJiraIssue`: `status.name` and `assignee.accountId` match
   what was requested; report a mismatch as a failure, not a success. Record the final `status.name`
   and assignee for Step 11.
No Jira comment other than the evidence comment unless the user approves the exact text first.
