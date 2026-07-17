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
- **Manual, per-repo install.** speckit isn't a plugin — every project needed its `.specify/` scripts,
  templates, and all nine command files copied in by hand and kept in sync. Onboarding a new repo (or
  a new teammate) meant repeating that setup; a fix to one command had to be re-copied everywhere.
- **Shallow plans.** speckit's `plan.md` was largely a template fill — it didn't read the real code, so
  paths and symbols were often guessed and went stale.
- **Not built for our shape.** speckit assumes a single repo; our platform is a **multi-submodule**
  layout (BE + web FEs + mobile) coordinated from an orchestration root, on **Bitbucket + Jira**, not
  GitHub.

**What shipkit changes.**

- **One file per feature** — `specs/NNN-slug/spec.md` holds goal · requirements · plan · tasks ·
  contracts · edge cases. Spec lives in git (diffable, reviewable, traceable), not buried in Jira.
- **One everyday command** — `/run-pipeline <ticket>` drives the whole flow; the stage skills exist
  for when you want a single step.
- **Installs in seconds** — it's a Claude Code plugin: two commands (`/plugin marketplace add` +
  `/plugin install`) and the whole team has every skill. Updates are one `marketplace update`; fixes
  ship to everyone at once. No scripts or command files copied per repo — `/bootstrap` then writes a
  single `.shipkit/config.yml` per project.
- **Deeper, verified planning** — `/plan-deep` grounds in the **real submodule code** via an Explore
  agent, then runs parallel reviewer agents that **verify every file path and symbol exists** and
  catch missed edge cases / cross-submodule ordering *before* the plan is written. speckit's plan was
  a template fill; shipkit's is grounded and checked.
- **Built for our shape** — auto-detects which **submodules** a ticket touches (by grepping the code),
  fans out one PR per submodule + a parent PR, and bumps submodule refs — all on **Bitbucket**, with
  state tracked in **Jira** (no GitHub labels/auto-close).
- **Same SDD discipline, kept** — grounded + agent-verified plans, three-pass review, allowlist-gated
  PRs. Lighter artifacts, not a lighter process.
- **One standard across the company** — the same skills, the same one-file spec shape, and the same
  ticket → spec → plan → review → PR → bump pipeline in **every** repo (ai-roleplay, learningos, …).
  Specs and reviews look the same everywhere, onboarding a project or a teammate is "install the
  plugin," and an improvement to the workflow ships to every team at once. It **auto-detects** whether
  a repo is a plain **single repo** or a **submodule orchestration root** and adapts the flow
  accordingly — so the same plugin is the standard for *every* repo, not just submodule roots.

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
| `/design-pipeline <change> [--ticket <t>]` | UI/UX route — orchestrates the Impeccable companion (shape → craft → document) + required anti-pattern detect gate in the frontend submodule; produces a `DESIGN.md`. Requires the Impeccable plugin. |
| `/design-recon <artifact> [--ticket <t>]` | **Match a mockup** — drives a screenshot / HTML / auth-gated Claude design link in a real browser (Playwright MCP), reads *computed* styles, snaps to the project's Tailwind tokens, and writes `design-contract.md` (all breakpoints + states). Cheaper *and* more accurate than reading the mockup's HTML. |
| `/design-verify [--ticket <t>] [--url <route>]` | Close the loop — renders the *built* UI at every breakpoint, diffs computed styles against `design-contract.md`, and gates `PASS`/`FAILED` with per-token `expected → actual → fix`. Responsive breakage (overflow, non-stacking) always fails. |
| `/review-changes [--ticket <t>] [--pr <id>]` | Three-pass parallel review (correctness/security · style/docs · infra/ops) across affected submodules + drift check. Local mode prints findings; PR mode posts a locked Bitbucket comment. |
| `/pr-from-plan --ticket <ticket> [--implement]` | Fan out child PRs per submodule + parent PR (allowlist-enforced, test-gated); opt-in `--implement` writes the code via worktree agents first. Never merges. |
| `/bump-submodule <path>@<sha> --closes <ticket>` | Verify merged SHAs, bump submodule refs (rebase-safe), update/open the parent PR with a Bumps table, transition the Jira ticket on merge |

## Design fidelity loop (UI tickets with a mockup)

FE implementations drift from the design — wrong spacing/color, missing hover states, and (chronically)
**desktop-only layouts that break on mobile**. And reading a mockup's HTML to avoid that is both
expensive and unreliable (utility classes, CSS variables, and the cascade mean authored CSS ≠ what
renders). shipkit closes this with a measure-based loop:

```
/design-recon <mockup> --ticket AR-123     ← Half 1: open the mockup in a real browser (Playwright MCP),
      │                                       read COMPUTED styles, snap to the project's Tailwind tokens,
      │                                       write specs/NNN/design-contract.md (all breakpoints + states)
      ▼
   implement — the contract IS the styling brief (assemble known classes, not guesses)
      ▼
/design-verify --ticket AR-123 --url <route>   ← Half 2: render the BUILT UI at every breakpoint,
      │                                            diff computed styles vs the contract, gate PASS/FAILED
      ▼                                            with expected → actual → fix. Responsive breakage fails.
   fix → re-run until PASS → /review-changes → /pr-from-plan
```

**Three artifact tiers**, auto-detected: an **HTML file** or **public URL** → exact computed-style
capture; a **screenshot** → honest vision-estimate (marked `approx`, verified perceptually). Same
extractor runs both halves, so a diff is a real build gap, not two measurement methods.

**Playwright MCP** drives the browser. Its own headless Chromium handles HTML + public URLs with **no
extension**. Only an **auth-gated Claude design link** needs the [Playwright Chrome extension](https://chromewebstore.google.com/detail/playwright-extension/mmlmfjhmonkocbjadbfplnigmagldckm)
so the MCP attaches to *your* Chrome and reuses your logged-in session. The skills degrade cleanly when
it's absent (they block with a clear message, never fake a pass).

> Responsive is enforced two ways: `/design-verify` fails on live overflow/non-stacking at 375/768/1280,
> and `/review-changes` statically flags desktop-only diffs (hardcoded widths, no `sm:`/`md:` variants)
> **even on tickets without a contract**.

`/run-pipeline` folds this in as an **opt-in** gate: for a UI ticket it asks once whether to run
recon→verify (remembered for resumes); if you opt in, recon runs after the spec and verify gates
before PRs — a `FAILED` halts like a review blocker. Decline it, backend tickets, and `auto` runs skip it.

This is distinct from `/design-pipeline`, which *generates* a design via the Impeccable companion.
`/design-recon` is for when a design already exists and you must **match** it.

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
