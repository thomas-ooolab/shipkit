---
name: review-changes
description: Reviews code changes with three parallel passes (correctness/security, style/docs, infra/ops) under one rubric, across the affected submodules. Local mode (default) reviews the feature-branch diff and prints findings — no writes. PR mode reviews an open Bitbucket PR and posts a locked review comment. Checks drift against the spec's task allowlist. Not for writing specs/plans or fixing the issues found.
argument-hint: "[--ticket <jira-ticket>] [--pr <bitbucket-pr-url|id>] [--staged] [--auto]"
---

# shipkit · review-changes

Reviews a change with one three-pass rubric in two modes. **Local mode** (default) reviews the
feature-branch diff across affected submodules and prints findings to chat — posts nothing, writes
nothing. **PR mode** (`--pr`) reviews an open Bitbucket PR diff and posts a locked review comment.
One quality bar, two surfaces.

> **Cite-sources rule.** Every finding traces to a specific diff line or a confirmed rubric
> observation. Never report a finding not grounded in the diff.
>
> **Never-guess rule.** If the mode/target is ambiguous, AskUserQuestion. Don't assume a PR or ticket.
>
> **Forbidden language.** No "I think / probably / looks like." Say "confirmed in diff line N",
> "rubric: correctness", "user confirmed".

## Bounded scope
Reviews and reports findings. It does **not**: approve/merge (the engineer decides), **fix** what it
finds, or review specs/plans (use `/plan-deep`). In local mode it touches nothing — no comment, no
write.

## Write surface
- **Local mode:** writes nothing — no comment, no file, no git/Jira/Bitbucket call (read-only diff).
- **PR mode:** the locked review comment on the Bitbucket PR (Step 5); optional Jira pointer note.
**Forbidden side-effects (both modes):** no Edit/Write; no git mutation (read-only `diff`/`status`);
never merge/close/edit a PR; never transition a ticket. All three review agents are read-only.

---

## Dynamic context (injected)
```
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" resolve`
```
If `SHIPKIT_CONFIG_EXISTS=0`, stop: "Run `/bootstrap` first."

## Topology mode (auto)
Read `TOPOLOGY_MODE`. **`single-repo`** → review the **one** repo's diff (the `feat/<ticket>-…` branch
vs its base); findings use `submodule: <project>`; no per-submodule loop. **`meta-with-submodules`** →
the per-submodule flow below.

## Step 1 — Parse mode & target
Parse `$ARGUMENTS`:
- `--pr <url|id>` → **PR mode**; bind the Bitbucket PR. Resolve which submodule repo it belongs to.
- otherwise → **local mode**; `--staged` selects the index diff over the working-tree+committed diff.
- `--ticket <key>` → bind `TICKET` (used to locate the spec for drift + context). If absent, infer
  from the current branch name (`feat/<ticket>-…`); if still unknown, review proceeds without drift.
- `--auto` (PR mode) → `AUTO=true` (skips the posting gate only; never suppresses clarifications).

Locate the spec via `probe.sh state <TICKET>` → `SPEC` (used for drift + Key decisions context).

## Step 2 — Gather the diff (per affected submodule)
**Local mode:** for each affected submodule (from the spec's task tags, or every submodule with a
`feat/<ticket>-*` branch), collect its diff:
```bash
git -C <path> diff <default-branch>...HEAD        # committed on the feature branch
git -C <path> diff [--staged]                      # plus working-tree/staged
```
If all diffs are empty: "No changes to review." Stop.

**PR mode:** fetch the PR diff + head SHA via the Bitbucket API
(`$BITBUCKET_USERNAME`/`$BITBUCKET_APP_PASSWORD`): `GET .../pullrequests/<id>` and `.../diff`. On
failure: "Cannot read PR — confirm Bitbucket creds." Stop.

**Drift check (if `SPEC` known).** Compare changed files to the spec's `## Tasks` file paths
(allowlist). A changed file **not** in the allowlist and not an accepted generated artifact (e.g.
`make gen` output) → a `blocking` drift finding:
`{pass:"drift", finding:"<path> changed but not in the spec's task allowlist", severity:"blocking", submodule:"<sub>", file:"<path>", line:0}`.
If no spec: note "Drift check skipped — no spec on file."

## Step 3 — Three-pass parallel review
Read each affected submodule's `CLAUDE.md` (and the root `CLAUDE.md`) → `PROJECT_CLAUDE`.
In a **single message**, dispatch all three bundled agents (parallel), passing the combined diff
(tagged per submodule), `PROJECT_CLAUDE`, and the spec's `## Key decisions` when present:
- `Agent(subagent_type: "correctness-security-reviewer")`
- `Agent(subagent_type: "style-docs-reviewer")`  (runs on sonnet)
- `Agent(subagent_type: "infra-ops-reviewer")`
Each returns a JSON array of findings per its rubric. Wait for all three. Same rubric in both modes.

## Step 4 — Merge & deduplicate
Combine drift + pass 1/2/3 findings. Dedup:
- `line > 0` → dedup by `(submodule, file, line)`, keep higher severity.
- `line == 0` → dedup by `(submodule, file, finding)` so two distinct whole-file findings both survive.
Sort blocking first, then advisory. Group output by submodule.

## Step 4.5 — Posting gate (PR mode, interactive only)
Skip the gate when local mode, `AUTO=true`, or non-interactive. Otherwise render all findings under
`## Review` (blocking first), then ask in the **same message** (STOP-guard: findings must immediately
precede the question): AskUserQuestion `["Post this review to PR <id>?", "Post review", "Print to chat only", "Discuss first", "Cancel"]`.
- **Print to chat only / Cancel** → emit findings, post nothing.
- **Discuss first** → hold; before posting later, re-check the PR head SHA — if it moved, re-run Steps 2–4.

## Step 5 — Output
**Local mode:** print the structured findings (grouped by submodule, blocking first), then a summary
line: `<n> blocking, <m> advisory across <k> submodules — resolve blockers, then /pr-from-plan`.
Write nothing.

**PR mode:** post a locked review comment on the Bitbucket PR via the API, body starting with the
grep-stable anchor:
```
🔍 shipkit review (locked, <submodule> PR #<id> @ <head-sha>):
```
followed by the findings (blocking first). Refuse to post if the body still contains an unresolved
placeholder token. Then report: `<n> blocking, <m> advisory. <0 blocking ⇒ ready for review | resolve blockers and re-run>`.
Optionally add a one-line Jira pointer note. No labels (Bitbucket has none) — state is the comment.

## Gotchas
- **Local mode touches nothing** — safe on any working tree, headless included. Only PR mode posts.
- **Drift check needs the spec** — it compares changed files to the spec's task allowlist; skipped if
  no spec/ticket is resolvable.
- **Per-submodule** — diffs, findings, and the `submodule` field keep a cross-service change readable
  per repo. Works for ai-roleplay's 3 submodules or learningos's larger set.
- **Three bundled agents** dispatched in one message; dedup by `(submodule, file, line)` with the
  `line:0` finding-text carve-out before output.
- **Reports only** — never fixes; never merges.
