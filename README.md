# shipkit

**Lightweight spec-driven development for Claude Code.**
One ticket, one guard-railed pipeline — from a lean one-file spec to merged PRs across submodules.

shipkit is the lighter successor to speckit. Instead of 9 commands generating 5–9 files per
feature, shipkit gives you **one everyday command** and **one spec file per feature**. Install it
once; no `.specify/` scripts or templates to copy into each repo.

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
| `/bootstrap` | One-time per-project setup → `.shipkit/config.yml` |
| `/run-pipeline <ticket>` | **Everyday skill** — ticket → scope → branches → one lean spec |
| `/spec-from-ticket <ticket>` | Just write the spec (no branches) |
| `/plan-deep --ticket <ticket>` | Verified, grounded plan into `spec.md` — Explore-agent grounding + parallel self-review & reference-verify, per-task submodule targets |
| `/review-changes` | Review the diff vs spec before PRs |
| `/pr-from-plan --ticket <ticket> [--implement]` | Fan out child PRs per submodule + parent PR (allowlist-enforced, test-gated); opt-in `--implement` writes the code via worktree agents first. Never merges. |
| `/bump-submodule <path>@<sha> --closes <ticket>` | Bump submodule refs after child PRs merge |

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
