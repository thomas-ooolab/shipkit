---
name: bump-submodule
description: After child PRs merge, bump the parent repo's submodule pointer(s) to the merged commit and open (or update) the parent bump PR. Closes the loop — when the bump PR merges, the ticket is done.
argument-hint: "<path>@<sha> [<path>@<sha> ...] --closes <jira-ticket>"
---

# shipkit · bump-submodule

Read `.shipkit/config.yml`. `$ARGUMENTS` is one or more `path@sha` pairs (the merged commit on
each submodule's tracking branch) plus `--closes {ticket}`.

> Run this only **after** the child PRs have merged. Bumping to an unmerged sha breaks the parent.

## Step 1 — Verify each sha is merged
For each `path@sha`, confirm the sha exists on the submodule's tracking branch:
```bash
git -C <path> fetch origin <branch>
git -C <path> merge-base --is-ancestor <sha> origin/<branch> && echo "merged" || echo "NOT merged — stop"
```
If any is not merged, stop and report which ones.

## Step 2 — Bump the pointers
On the parent feature branch (`feat/{ticket}-{slug}`):
```bash
git -C <path> checkout <sha>          # detach submodule at the merged sha
git add <path>                         # stage the new pointer
# repeat per path@sha
git commit -m "chore: bump {paths} for {ticket}"
git push
```

## Step 3 — Open / update the parent bump PR
- If the parent PR from `/pr-from-plan` is still open, this push updates it.
- Otherwise open it now: title `{ticket}: {feature title}`, body links the merged child PRs + spec.
- Target `main` (or `staging` first if that's the project gate).

## Step 4 — Close the ticket
When the parent bump PR merges, the feature is shipped. If Atlassian MCP is connected, transition
the Jira ticket (e.g. → Done) and comment with the merged parent PR URL. Otherwise tell the user
to transition `{ticket}` manually.

## Step 5 — Report
```
Bumped: {path}@{short-sha} (+ ...)
Parent PR: {url}  → merge to finish
Ticket {ticket}: {transitioned to Done | transition manually}
```
