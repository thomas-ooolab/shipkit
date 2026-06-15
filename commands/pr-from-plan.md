---
description: Open one Bitbucket PR per affected submodule for the ticket, plus the parent-repo PR. Each child PR references the Jira ticket; the parent PR links all child PRs. Run after /review-changes passes.
argument-hint: "[--ticket <jira-ticket>] [--target staging|main]"
---

# shipkit · pr-from-plan

Read `.shipkit/config.yml` and the spec. Fan out PRs based on the per-task `Targets:` and the
branches created by `/run-pipeline`. Default PR target is `staging` (validation) unless `--target main`.

> Bitbucket has no GitHub-style "Closes #N" keyword. Linking the Jira ticket = put the ticket key
> in the branch name + PR title, and (if Atlassian MCP connected) transition the ticket on merge.

## Step 1 — Push branches
For each affected submodule, commit (if needed) and push its `feat/{ticket}-{slug}{suffix}` branch.
Push the parent repo branch too.

## Step 2 — Open one child PR per affected submodule
Use the Bitbucket API (`$BITBUCKET_USERNAME` / `$BITBUCKET_APP_PASSWORD`) per `remote.workspace`:
- **Title:** `{ticket}: {feature title} ({service})`
- **Source:** `feat/{ticket}-{slug}{suffix}` → **Dest:** `staging` (or `main`)
- **Body:** link the Jira ticket, list the REQ-IDs covered, link the spec path.
- ⚠️ Skip `staging_only` submodules targeting `main` — warn the user instead.

## Step 3 — Open the parent-repo PR
- **Title:** `{ticket}: {feature title}`
- **Body:** the canonical summary + **links to every child PR** grouped by service + spec path.
  The parent PR is the throughline that ties the child PRs to the ticket.
- Note: the parent's submodule-ref bump happens **after** child PRs merge — see `/bump-submodule`.

## Step 4 — Report
List every PR URL grouped by service, the dest branch, and the remaining gate:
```
Child PRs must merge → then: /bump-submodule <path>@<sha> --closes {ticket}
```
If Atlassian MCP is connected, post the PR links as one comment on the Jira ticket.
