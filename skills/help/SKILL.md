---
name: help
description: "Use when the user asks how to use shipkit, which skill or command to run for what they want to do, what order the skills go in, or which shipkit version is installed. Trigger: /shipkit:help [<what you want to do>]. Examples: \"/shipkit:help\", \"/shipkit:help QC reported a bug on AR-450\", \"shipkit: how do I ship a ticket from start to finish?\", \"which shipkit version is installed?\""
argument-hint: "[<use case in your own words>]"
---

# shipkit · help

Shows the installed shipkit version and **drafts the instructions for the user's use case**: which skills
to run, in what order, with the user's own ticket / URL filled in. Read-only — it never runs the skills
it recommends, never writes a file, never calls Jira, Slack or Bitbucket.

## Step 1 — Version and skills (always first)
```bash
python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
ls "${CLAUDE_PLUGIN_ROOT}/skills"
```
Print `shipkit v<version> — <n> skills` as the first line. The `ls` is the **only** list of skills that
exist: recommend a skill only if its directory is listed.

## Step 2 — Pick the use case
Match the user's words (any language; answer in theirs) to one row. Nothing given → print the table's
first column only and ask which one applies. Nothing fits → say so plainly and show the table; never
improvise a workflow.

| Use case | Skills, in order |
|---|---|
| First time in a repo | `/fix-permissions` → `/bootstrap` |
| Ticket → merged PRs, end to end | `/run-pipeline <ticket>` — it runs the stages below and stops at the open-questions, implement and merge gates |
| Same flow, one step at a time | `/spec-from-ticket` → `/cross-check` → `/clarify` (only if questions are open) → `/plan-deep` → implement (`/assign` when ≥2 submodules) → `/verify` → `/review-changes` → `/pr` → `/merge` → `/bump-submodule` |
| Ticket is unclear / PO must answer | `/cross-check` → `/clarify` |
| UI ticket with a mockup | `/design-recon` → implement → `/verify` (it also diffs the built UI against the design contract) |
| QC / tester reported a bug in a Jira comment | `/run-pipeline <ticket> --bug` — runs the bug stages below, stops at the merge gate |
| Bug fix, one step at a time | `/bugfix <ticket>` (it calls `/verify` itself) → `/review-changes` → `/pr` → `/merge` → `/bump-submodule` |
| Prove a feature or fix works | `/verify --ticket <ticket>` |
| Review code before a PR | `/review-changes` |
| Open PRs / land them | `/pr` → `/merge` → `/bump-submodule` |
| Answer Slack questions as the developer | `/developer <thread-url>` (one thread) · `/developer` (observer, drafts) · `/developer <ticket>` (start work) |

## Step 3 — Draft the instructions
For the chosen row, output:
1. **Goal** — one line, in the user's words.
2. **Steps** — numbered. Each: the command with the user's real ticket key / URL / path filled in (leave
   `<placeholder>` only for what they didn't give), plus one line on what it does and what it leaves
   behind (spec file, branch, evidence, PR).
3. **Before you start** — only what this case needs and the user may lack: `.shipkit/config.yml`
   (`/bootstrap`), `JIRA_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN`, `SLACK_REVIEW_TOKEN` /
   `SLACK_APP_TOKEN` (`/developer`, `/pr`), a running FE/BE (`/verify`, `/bugfix`). Never print or ask
   for a token value; say which variable to export.
4. **Stops** — where the user must act: approval prompts, the implement gate, `/merge`'s confirmation.

Flags and arguments come from each cited skill's `argument-hint` and description in
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` — read them, don't recite from memory, so the draft
matches this version. A flag you didn't read there is not in the draft.

Argument is a skill name (`/shipkit:help verify`) → skip the table: show that skill's description and
`argument-hint`, and where it sits in the flow.

## Gotchas
- **Namespace.** Claude Code has its own `/help`; this one is `/shipkit:help`.
- **Version source** is `.claude-plugin/plugin.json` of the *installed* plugin, not the repo checkout the
  user may be editing.
- **Don't promise behavior** the skills' files don't state (timings, auto-merge, who gets notified).
