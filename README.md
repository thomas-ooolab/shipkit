# shipkit

**Lightweight spec-driven development for Claude Code.**
One ticket, one guard-railed pipeline — from a lean one-file spec to merged PRs across submodules.

shipkit is the lighter successor to speckit. Instead of 9 commands generating 5–9 files per
feature, shipkit gives you **one everyday command** and **one spec file per feature**. Install it
once; no `.specify/` scripts or templates to copy into each repo.

---

## Why shipkit, not speckit?

**The problem.** We adopted speckit for spec-driven development, but it was too heavy for day-to-day
work:

- **Too many artifacts.** Every feature spawned 5–9 files (`spec.md`, `requirements.md`, `plan.md`,
  `contracts.md`, `tasks-*.md`, `research.md`, `data-model.md`, checklists…). Most got skimmed once
  and went stale — more to write and maintain than to read.
- **Too many commands.** Nine `/speckit.*` steps to drive a single feature through.
- **Per-repo setup.** Each repo needed `.specify/` scripts + templates copied in and kept in sync.
- **Not built for our shape.** speckit assumes a single repo; our platform is a **multi-submodule**
  layout (BE + web FEs + mobile) coordinated from an orchestration root, on **Bitbucket + Jira**, not
  GitHub.

**What shipkit changes.**

- **One file per feature** — `specs/NNN-slug/spec.md` holds goal · requirements · plan · tasks ·
  contracts · edge cases. Spec lives in git (diffable, reviewable, traceable), not buried in Jira.
- **One everyday command** — `/run-pipeline <ticket>` drives the whole flow; the stage skills exist
  for when you want a single step.
- **Install once, configure once** — it's a Claude Code plugin; `/bootstrap` writes a single
  `.shipkit/config.yml` per project. No scripts copied per repo.
- **Built for our shape** — auto-detects which **submodules** a ticket touches (by grepping the code),
  fans out one PR per submodule + a parent PR, and bumps submodule refs — all on **Bitbucket**, with
  state tracked in **Jira** (no GitHub labels/auto-close).
- **Same SDD discipline, kept** — grounded + agent-verified plans, three-pass review, allowlist-gated
  PRs. Lighter artifacts, not a lighter process.

(Full side-by-side in [What's different from speckit](#whats-different-from-speckit) below.)

---

## Install (private Bitbucket)

```bash
# in Claude Code
/plugin marketplace add git@bitbucket.org:ooolab-learningos/shipkit.git
/plugin install shipkit@shipkit
```

Auth uses your existing `git` credentials (SSH key / credential helper). For background
auto-update, export an app password: `export BITBUCKET_TOKEN=<app-password>`.

---

## Day-to-day

```bash
/fix-permissions           # ONCE per repo — allow shipkit's read-only probe (see Permissions)
/bootstrap                 # once per project — writes .shipkit/config.yml
/run-pipeline AR-123       # every feature — the whole pipeline in one command
```

`/run-pipeline` fetches the Jira ticket, detects which submodules are affected, creates the
branches, and writes **one** lean `specs/NNN-slug/spec.md` (goal · requirements · plan · tasks ·
contracts · edge cases). Then you implement, review, and open PRs.

---

## The pipeline

```
/run-pipeline AR-123
      │  (fetch ticket → detect scope → branch → write one lean spec.md)
      ▼
   implement in submodule branches
      ▼
/review-changes            check diff vs spec (REQ coverage, discipline)
      ▼
/pr-from-plan              one child PR per submodule + parent PR, all ref AR-123
      ▼
   child PRs merge
      ▼
/bump-submodule path@sha --closes AR-123    bump parent refs → parent PR merges → ticket done
```

## Skills

Each is a plugin **skill** (`skills/<name>/SKILL.md`) — invoke explicitly with `/name`, or let Claude
auto-trigger it by description.

| Skill | Role |
|---|---|
| `/fix-permissions` | One-time per-repo — allow the read-only probe so injected context can run |
| `/bootstrap` | One-time per-project setup → `.shipkit/config.yml` |
| `/run-pipeline <ticket>` | **Everyday skill** — ticket → scope → branches → one lean spec |
| `/spec-from-ticket <ticket>` | Just write the spec (no branches) |
| `/plan-deep --ticket <ticket>` | Verified, grounded plan into `spec.md` — Explore-agent grounding + parallel self-review & reference-verify, per-task submodule targets |
| `/review-changes [--ticket <t>] [--pr <id>]` | Three-pass parallel review (correctness/security · style/docs · infra/ops) across affected submodules + drift check. Local mode prints findings; PR mode posts a locked Bitbucket comment. |
| `/pr-from-plan --ticket <ticket> [--implement]` | Fan out child PRs per submodule + parent PR (allowlist-enforced, test-gated); opt-in `--implement` writes the code via worktree agents first. Never merges. |
| `/bump-submodule <path>@<sha> --closes <ticket>` | Verify merged SHAs, bump submodule refs (rebase-safe), update/open the parent PR with a Bumps table, transition the Jira ticket on merge |

## Permissions (run `/fix-permissions` first)

shipkit skills load context by auto-running `!`bash …/probe.sh …`` at invocation. Claude Code won't
run an **injected** shell command unless it's pre-authorized, and injected commands can't show the
interactive approval prompt — so without the allow-rule, `/bootstrap` fails with *"command requires
approval"*.

`/fix-permissions` resolves a bundled applier and **prints a terminal command for you to run** — a
command *you* run is your own action and bypasses the injection/classifier block, whereas a command
the model runs would hit the same wall. Run it **once** before `/bootstrap`:

```bash
bash "$(find ~/.claude/plugins -name apply-permissions.sh 2>/dev/null | sort -V | tail -1)" --user
```

`--user` writes `~/.claude/settings.json` — covers **every** repo at once, and is the scope a
`/pr-from-plan --implement` **background worktree agent** reads. (`--project` writes the repo's
`.claude/settings.json` instead; commit it to share with the team.) The key rule is `Bash(bash:*)` —
the plugin lives at a versioned cache path, so a path-scoped rule would break on every update. The
applier is idempotent and backs up before writing.

## Spec = source of truth in git

Specs are git-tracked files (`specs/NNN-slug/spec.md`), not Jira comments — so they diff, review,
and trace alongside the code. Jira gets a short pointer comment + status transition only.

## What's different from speckit

| | speckit | shipkit |
|---|---|---|
| Commands | 9 (`/speckit.*`) | 1 everyday (`/run-pipeline`) + 5 stages |
| Files per feature | 5–9 (spec, requirements, plan, contracts, tasks-*, research, …) | **1** (`spec.md`) |
| Per-project setup | copy `.specify/` scripts + templates | `/bootstrap` writes one config file |
| Distribution | per-repo | install the plugin once |
| Vocabulary | issue | **ticket** (Jira) / **PR** (Bitbucket) |
