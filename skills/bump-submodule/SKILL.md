---
name: bump-submodule
description: After child PRs merge, bump the parent repo's submodule pointer(s) to explicit merged commits and open or update the parent PR that ties the feature to the ticket. Pins each submodule via <path>@<sha> (path is whatever .gitmodules declares). Rejects --to-default-branch-head combined with --closes. Transitions the Jira ticket on merge. Not for single-repo projects.
argument-hint: "<path>@<sha>… [--closes <jira-ticket>] [--to-default-branch-head] [--replace]"
---

# shipkit · bump-submodule

Updates one or more submodule gitlinks in the **parent** repo to specific commits, then opens (or
updates) the parent PR that links the feature to the ticket. Used by `/run-pipeline` after the
child PRs merge; also runnable manually.

> **Cite-sources rule.** Every bumped path traces to a confirmed SHA — explicit `<path>@<sha>`, or
> resolved from the submodule's upstream HEAD under `--to-default-branch-head` (logged in the Bumps
> table). Verify each SHA is actually merged before bumping.
>
> **Never-guess rule.** Reject `--closes` with `--to-default-branch-head` (non-deterministic SHA →
> the ticket transition would race). Reject a duplicate open bump PR without `--replace`.
>
> **Forbidden language.** No "I think / probably." Say "confirmed merged via merge-base", "resolved
> to <sha>", "user confirmed via --replace".

## Bounded scope
For submodule (multi-repo) projects only. It does **not**: implement code (`/pr-from-plan`), or
**merge** anything (opens/updates a PR for review). Single-repo → error out.

## Write surface (the ONLY things written)
1. Parent repo: each named submodule checked out to its explicit SHA, the staged pointer updates,
   one commit, one pushed branch (the ticket's parent branch, or a `bump/<ticket>` branch if none).
2. One parent Bitbucket PR (created, or updated if it already exists); with `--replace`, decline the
   superseded bump PR.
3. On the parent PR merging: the Jira ticket transition (if Atlassian MCP connected).
**Forbidden side-effects:** never merge a PR; never edit submodule code or any parent file beyond the
pointers; no test/build execution.

---

## Dynamic context (injected)
```
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" resolve`
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" topology`
```
If `SHIPKIT_CONFIG_EXISTS=0`, stop: "Run `/bootstrap` first." If `GITMODULES_EXISTS=0`, stop:
"`/bump-submodule` requires a submodule project; this is single-repo — use a regular PR."

## Step 1 — Parse & validate
Parse `$ARGUMENTS`:
- `BUMPS[]` — `<path>@<sha>` pairs (or bare `<path>` with `--to-default-branch-head`). `path` must be
  one declared in `.gitmodules` (check against the probe `topology` paths). Unknown → stop:
  "`<path>` is not a declared submodule."
- `CLOSES` — the Jira ticket after `--closes` (e.g. `AR-123`), or empty.
- `MODE` — `pinned` (default) or `remote` (`--to-default-branch-head`).
- `REPLACE` — true if `--replace`.

Reject `MODE=remote` + `CLOSES` set: "`--to-default-branch-head` cannot combine with `--closes` —
the SHA is non-deterministic, so the ticket transition would race. Pin an explicit `<path>@<sha>`."
If no `BUMPS` → AskUserQuestion for at least one `<path>@<sha>`.

## Step 2 — Verify each SHA is merged
For each `path@sha` (pinned mode), confirm the sha is on the submodule's tracking branch:
```bash
git -C <path> fetch origin <branch>
git -C <path> merge-base --is-ancestor <sha> origin/<branch> && echo merged || echo NOT-merged
```
Any `NOT-merged` → stop and list them (bumping to an unmerged sha breaks the parent). In `remote`
mode instead resolve the sha: `git -C <path> submodule? ` → fetch + `rev-parse origin/<branch>`, and
record the resolved sha for the Bumps table.

## Step 3 — Concurrency check
List open parent PRs whose body mentions a `Bumps:` row for the same submodule path (Bitbucket API
search). If a duplicate exists and `REPLACE` is false → stop with its URL: "Open bump PR already
exists for `<path>` — resolve it, or re-run with `--replace`." If `REPLACE` → decline the superseded
PR with an explanatory comment.

## Step 4 — Bump the pointers (rebase first)
Work on the ticket's parent branch (`feat/<ticket>-<slug>` if it exists, else create
`bump/<ticket>`). Rebase on the parent default branch first so a just-merged parent change doesn't
conflict:
```bash
git fetch origin && git rebase origin/<default-branch>
# per path@sha (capture BEFORE for the Bumps table):
BEFORE=$(git ls-tree HEAD <path> | awk '{print $3}')
git -C <path> checkout <sha>
git add <path>
# repeat per path
git commit -m "chore(submodules): bump <paths> for <ticket>"
git push   # (--force-with-lease only if the branch was rebased)
```

## Step 5 — Open or update the parent PR
- If a parent PR for the ticket already exists (opened by `/pr-from-plan`): the push **updates it** —
  refresh its description with the Bumps table.
- Else open one on the parent repo via the Bitbucket API:
  - **Title:** `<ticket>: bump <paths>`
  - **Body:** the `Bumps:` table + links to the merged child PRs + the spec path + the ticket link.
```
Bumps:
| Submodule | From | To |
|---|---|---|
| ai-roleplay-be | <before> | <sha> |
```
Not opened as `[WIP]` — a bump PR is review-ready. (Bitbucket has no auto-close keyword; the ticket
key in the title is the link.)

## Step 6 — Close the loop
Report:
```
✅ Bump PR: <url>   (paths: <path@sha, …> · closes: <ticket|none>)
When it merges → the feature is shipped.
```
When the parent PR merges: if Atlassian MCP is connected and `CLOSES` was set, transition the ticket
to `jira.done_transition` and comment the merged PR URL. Otherwise tell the user to transition
`<ticket>` manually. `/run-pipeline` reads the bump PR URL from this report.

## Gotchas
- **Verify-merged is mandatory.** Bumping to an unmerged sha leaves the parent pointing at a commit
  nobody else can fetch. Step 2 guards this.
- **Rebase before bumping.** A parent change merged seconds earlier would otherwise conflict on the
  gitlink.
- **`--to-default-branch-head` is non-deterministic** — two runs minutes apart can capture different
  shas; that's why it can't auto-transition a ticket (`--closes` is rejected with it).
- **Ticket transition replaces GitHub's auto-close.** Bitbucket has no closing keyword; the Jira
  transition on merge is how the ticket reaches Done.
- **Path-agnostic.** Works for whatever `.gitmodules` declares — ai-roleplay's 3 submodules or
  learningos's larger set; never assumes a path prefix.
