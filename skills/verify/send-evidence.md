# /verify — Step 7: send the evidence (`--send-evidence`)

> Loaded by SKILL.md only in send mode (`--send-evidence`), which only `/merge` passes. Never run at any other point of a verify run.

## Step 7 — Send the evidence (send mode: `--send-evidence`, called by `/merge` before it changes the status)
Reads the saved draft; drives no app and re-checks nothing. The draft is the newest `.shipkit/evidence/<TICKET>/jira-comment-*.md`
whose first header cell is `/verify` (a bug fix's table starts with `Concern` and is never sent from here). None → send nothing and say
`no evidence draft — run /verify --ticket <TICKET> first`. A person running it by hand outside `/merge` is the
only other case; never send at any other point of a verify run.
1. **Find the existing evidence comment first — there is only ever one.** Look up its id:
   (a) `.shipkit/evidence/<TICKET>/jira-comment-id`, if present; else (b) scan the ticket's comments
   (`getJiraIssue` with comments) for one whose body is a table with `/verify` as its first header cell. Found
   (a) or (b) → this run is an **edit**. Several found → edit the newest and tell the user about the extras.
   None found, and no id file → this is the **first post**. An id file exists but its comment is gone (deleted)
   → don't post: ask the user whether to create it anew.
2. **Check the draft is complete — then send it without asking.** The format is already agreed (Step 6), so a draft
   that meets it needs no approval. Complete = (a) one table, first header cell `/verify`, nothing else; (b) one
   row per check and every result cell `✅ PASS`; (c) no "not checked / only covered by a unit test"
   row; (d) every `![caption](path)` points at an existing PNG, every FE row has at least one, every BE row holds a
   redacted excerpt with no token, credential or personal data; (e) the `UI` row is present when Part A ran. All
   hold → print the exact text and the attachment list, labelled **"EDIT comment <id>"** or **"POST the first
   evidence comment"**, for the record, and go straight to step 3. Any one fails → send **nothing**; report
   `Jira <TICKET>: evidence NOT sent — incomplete: <which row / what is missing>` (a problem, so the caller asks).
3. Send it (PNG only, each opened and checked before it is embedded):
   - first post: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" post <TICKET> --file <draft.md>`
     then save the printed comment id to `.shipkit/evidence/<TICKET>/jira-comment-id`;
   - re-run: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" edit <TICKET> <COMMENT_ID> --file <draft.md>`
     — the body is replaced in place; the table always shows the **latest** result of every row.
   The script reads the saved comment back and prints `"images": {"in_table": n, "outside_table": m}`: `in_table`
   must equal the screenshots you embedded and `outside_table` must be `0` — otherwise say so, don't report it done.
   **Never run `post` when an evidence comment exists, not even if `edit` fails** — an edit that errors (exit 4,
   e.g. the comment belongs to someone else) → stop, tell the user the evidence was **not** updated and why.
   Exit 3 (Jira env unset) → don't skip silently and don't fall back to a mention-less MCP comment: tell the user
   the evidence was **not** posted/updated, why, and that the files are in `.shipkit/evidence/<TICKET>/`.
   Exit 5 = sent but a mention didn't land — say so.
4. Report (this line is what `/merge` reads back): `Jira <TICKET>: evidence comment <posted|edited> <permalink>`,
   `Jira <TICKET>: evidence NOT <posted|updated> — <reason>`, or the `evidence NOT sent — incomplete: …` line of step 2.
