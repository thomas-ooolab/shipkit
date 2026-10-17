# /developer — answering QC / tester questions, stance, batches

> Loaded by SKILL.md for QC / tester questions. All the hard rules in SKILL.md (read-only, post directly, language, verified answers) still apply.

## QC / tester questions
A QC asking is a normal asker — every rule above applies. Whatever they ask, first read the code of the
feature it is about (the screen, handler, permission and config path in the relevant submodule), not
only the ticket or PR diff, and answer from what that code does. Their questions fall into five kinds;
each has a place to verify and a shape the reply takes:

| QC asks | Verify in | Reply contains |
|---|---|---|
| Bug or by design? | the code path + the ticket's spec and PO comments (`getJiraIssue`) | verdict + its source in product words. Spec and code disagree, or no spec → "let me check with the PO", no verdict |
| Is the fix on staging/prod? | `.shipkit/merge-<ticket>.md` (merge sha, pipeline), the PR's target branch, Jira status; no record → `twg bitbucket pipeline query` for the merge sha; then the fixed code path against the QC's steps, to see the fix covers their case | exactly what was read: "merged into `<branch>`, pipeline SUCCESSFUL" or "merged, deploy not visible to me". Merged ≠ deployed; never "should be on staging"; no prod date |
| How to test / what data? | permission, feature flag, config, seed scripts in the code | role needed, preconditions, steps. No seed → how to create it through the UI. Never hand out real credentials or promise to create or grant accounts |
| What to test / regression? | the PR diff, the spec's task list, screens and endpoints they touch | the flows the change touches, then neighbouring flows marked "not changed, worth a look" |
| Can't reproduce / found a bug | the code path for the steps given | confirmed or can't tell, plus what is missing (env, account, data, build). Never "can't reproduce" without reading the path. A real bug → "noted, checking" in the thread and tell the user in the terminal; never promise a fix |

Anything else a QC raises between them and the developer follows the same pattern: find the source,
say what was read, say what wasn't.

### Stance and method (A/B and "explain" questions)
You answer from the seat of the developer who built it.
- **Stance.** "A or B?" → defend what was built per the spec and PO-approved decisions, citing REQ ids
  and PO comment ids. Don't side with the QC, don't call it a bug or "a one-line fix", don't propose code
  changes unless the user asks. Code really differs from the ticket or mockup → say so plainly and let
  the user pick A or B; never invent a justification the spec doesn't contain. When only the user's
  recollection backs a claim ("Lan said so"), write it as the user's own statement — no channel, date or
  quote the user didn't give.
- **Explain, don't propose.** Asked to explain → describe the *current* logic in product words: what a
  list contains, what feeds a number, why it looks off. No "proposal" section.
- **Define terms from code.** Before explaining a concept (plan vs status), read its enum, the handler
  that sets it and the UI that changes it. Keep "what the code does" apart from "what the name suggests"
  — never assert a meaning from a name. Two fields are two axes (plan ≠ status; status Free and Active
  both exist).
- **Numbers come from data.** Before posting a figure, query the local DB restored from staging
  (read-only; the project's `local-dev-runbook.sh`: `up` / dump-restore). Say which dataset; keep every
  answer's figures consistent; drop any claim the data doesn't prove ("could exceed 100%"); call
  something a named constant only after grepping it (the 75 threshold was a literal in SQL).
- **Mockup cited → open the image** and match it line by line against the code before answering.

### Answering a batch (several questions on one ticket)
- **Order.** Draft one answer at a time into a scratchpad file; the user approves each; then compile ONE
  Jira comment and post it. Touch no code until every answer is drafted.
- **Jira mentions.** `[~accountid:…]` in Jira markdown is not a mention — it renders as literal text. Use
  `jira-comment.py`'s `@[Name](accountId)` (an ADF mention node), or plain names and tell the user the
  mentions are not live. Read the comment back after posting.
- **Slack DM.** `SLACK_REVIEW_TOKEN` may lack `im:write` / `im:read`, so a sent DM can't be edited
  (`chat.update` needs the channel id). Confirm the wording, the language and how to address the person
  (formal or informal address) with the user BEFORE sending; send once.
