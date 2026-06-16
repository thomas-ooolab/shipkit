---
name: design-pipeline
description: "Orchestrates the Impeccable design pipeline (shape, craft, document, then the anti-pattern detect gate) for any UI/UX or frontend change — components, styling, layout, visual work — in a frontend submodule (or the repo, single-repo mode). Produces a spec-compliant DESIGN.md and runs the detect gate. Impeccable is a companion plugin; for a confirmed UI/UX change the gate is REQUIRED and blocks when Impeccable is absent/disabled. Not for backend/logic changes, non-visual refactors, or reviewing an open PR."
argument-hint: "<what UI/UX to change> [--paths <dir>] [--ticket <jira-ticket>]"
---

# shipkit · design-pipeline

Orchestrates the Impeccable design pipeline for a UI/UX change: establish design context, build the
change, document a spec-compliant `DESIGN.md`, and run the anti-pattern detect gate — then report.
For a confirmed UI/UX change this is a **required gate**: when Impeccable is absent/disabled the skill
**blocks** (it does not skip), so an ungated UI/UX change never ships. Only a non-applicable target
(non-visual / no frontend) bails gracefully.

> Impeccable is a **separate companion plugin** (not bundled with shipkit). shipkit invokes it; it does
> not install it. If it's missing, this skill guides you to enable it — it never vendors it inline.

> **Cite-sources rule.** Every result traces to a confirmed observation: a command's actual output
> (`npx impeccable detect` exit + lines), a file Read, or a user answer. Never invent findings or a
> `DESIGN.md` path that wasn't produced.
>
> **Never-guess rule.** If the change target is missing/ambiguous, AskUserQuestion. Don't assume which
> component, page, or submodule to work on.
>
> **Forbidden language.** No "I think / probably / looks like." Say "detect reported N issues",
> "Read returned DESIGN.md", "user confirmed the target".

## Bounded scope
Drives a design-quality pipeline for visual changes. It does **not**: touch backend/business-logic
code (`/plan-deep` + `/pr-from-plan`), install/vendor Impeccable, or open a PR / post to Bitbucket — it
ends at a `DESIGN.md` + detect gate; commit/PR is your next step (or `/run-pipeline`).

## Write surface (the ONLY things written)
1. Working-tree UI/component edits + the generated `DESIGN.md` — both delegated to Impeccable's
   `craft` / `document` subcommands; this skill edits nothing directly.
**Forbidden side-effects:** no git mutation; no Bitbucket/Jira call (no PR, comment, transition); no
backend edits; no plugin installation; no config writes.

---

## Dynamic context (injected)
```
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh" resolve`
```

## Step 1 — Scope the change (which submodule + paths)
Parse `$ARGUMENTS`: the change description + optional `--paths <dir>` and `--ticket <key>`.
- **Resolve the frontend target.** Read `TOPOLOGY_MODE` from the probe.
  - `meta-with-submodules` → pick the affected **frontend** submodule (a `react`/`nextjs` stack in
    config — e.g. vle-frontend, clms-frontend, ai-roleplay). If a `--ticket` is given, use its spec's
    `services` to choose; if two FE submodules are plausible, AskUserQuestion which one. `PATHS`
    defaults to that submodule's frontend source root (or the `--paths` value, resolved inside it).
  - `single-repo` → `PATHS` defaults to the repo's frontend source root (or `--paths`).
- If `--ticket` resolves a spec, forward its `## Key decisions` into `KEY_DECISIONS` so the build honors
  the confirmed structural choices and stays within `PATHS`.
- If no target is given → AskUserQuestion for the component/page/path.
- If the change is clearly non-visual (backend/API/data/infra) → AskUserQuestion
  `["This targets non-visual code, where Impeccable's design pipeline doesn't apply. Proceed anyway, or cancel?", "Proceed", "Cancel"]`.

## Step 2 — Preflight Impeccable (REQUIRED gate, headless-safe)
Detect availability:
```bash
npx --no-install impeccable --version 2>/dev/null && echo IMPECCABLE_OK || echo IMPECCABLE_ABSENT
```
If inconclusive, cross-check `claude plugin list 2>/dev/null | grep -i impeccable`.
- `IMPECCABLE_OK` → Step 3.
- `IMPECCABLE_ABSENT` (absent or disabled) on a confirmed UI/UX target — the gate is **required**, do
  NOT proceed:
  - **Interactive** → AskUserQuestion `["Impeccable is required for this UI/UX change but isn't installed/enabled. Enable it?", "Enable impeccable@impeccable (claude plugin enable impeccable@impeccable)", "Install it from its marketplace first", "Cancel — don't ship an ungated UI/UX change"]`. Re-run the probe after enabling; only `IMPECCABLE_OK` advances. Cancel → emit `design-pipeline: BLOCKED — Impeccable required for <target>`.
  - **Non-interactive** (no TTY / auto mode) → **hard-fail**: emit
    `design-pipeline: BLOCKED — Impeccable required but absent/disabled for <target>` and tell the user
    to `claude plugin enable impeccable@impeccable` and re-run. Never skip the design steps; never emit
    a "gate not enforced" pass.

`BLOCKED` is a grep-stable terminal `/run-pipeline` reads to halt.

## Step 3 — Run the Impeccable pipeline (in order)
Run each, capture and cite its output, advance only on success. `/impeccable` subcommands are
space-separated. When `KEY_DECISIONS` is non-empty, forward it into `shape`/`craft` so the build
honors the confirmed choices within `PATHS`.

a. **Context** — `/impeccable teach` to establish/refresh project design context. Skip if a `DESIGN.md`
   already exists for the target (note "design context present").
b. **Direction** — `/impeccable shape` for brand toolkit + direction. Run for a new surface; skip a
   tweak to an already-shaped surface.
c. **Build** — `/impeccable craft` to implement the change in code (inside `PATHS`).
d. **Iterate (optional)** — `/impeccable live` for in-browser refinement. Needs a running dev server;
   probe first, and if none, **skip with a note** (never start a server, never prompt headless).
e. **Document** — `/impeccable document` to generate/update the spec-compliant `DESIGN.md`.

## Step 3f — Quality gate (detect + fix loop) — REQUIRED
```bash
npx impeccable detect "$PATHS"
```
Parse findings; cite each by `file:line`.
- Exit 0 / zero findings → gate **PASS**.
- Findings present → report them, run the fix loop: `/impeccable polish` (or `/impeccable audit` for a
  deeper pass), re-run `detect`, repeat until clean or the user stops. Non-interactive → **at most one**
  fix pass. Unresolved findings = gate **FAILED** (not pass-with-note): emit
  `design-pipeline: FAILED: N issue(s) for <target>` and stop (`/run-pipeline` halts on this).
- Non-zero for a non-findings reason (crash/bad args) → report raw output, mark **INCONCLUSIVE**; don't
  claim PASS, don't fabricate findings.

## Step 4 — Report
```
design-pipeline: <PASS | FAILED: N issue(s)> for <target>  (<submodule> | repo)
DESIGN.md:   <path, or "not generated">
Steps run:   teach / shape / craft / live / document / detect  (each: run or skipped + why)
Detect gate: PASS (0 findings) | FAILED: <file:line — rule> | INCONCLUSIVE (raw output)
Impeccable:  <version>
Next step: review the change, then /pr-from-plan --ticket <ticket> (or /run-pipeline <ticket>).
```

## How it fits the pipeline
For a UI/UX ticket, the design route is: `/design-pipeline <change> --ticket <T>` → (Impeccable builds
in the working tree + passes the detect gate) → `/pr-from-plan --ticket <T>` opens the PR from that
working tree. The design gate must PASS before the PR — a UI/UX change never ships ungated.

## Error handling
- **Impeccable absent/disabled** → block (interactive: enable/cancel; non-interactive: hard-fail
  `BLOCKED`). Never a "gate not enforced" pass.
- **Detect findings the fix loop can't clear** → gate FAILED; stop. Don't pass-with-note.
- **`detect` unparseable / crashes** → report raw output, mark INCONCLUSIVE. Don't claim PASS.
- **No dev server for `live`** → skip with a note. Never start a server.
- **Not a frontend target / no visual paths** → AskUserQuestion in Step 1; cancel → stop "No UI/UX
  target confirmed." (This non-applicability bail is distinct from the Impeccable-absent block.)

## Gotchas
- `/impeccable` subcommands are space-separated (`/impeccable craft`); `detect` is the **CLI**
  (`npx impeccable detect <paths>`), not a slash command.
- Impeccable is a **separate companion** — checked at runtime, never assumed. For a confirmed UI/UX
  change it's a **required gate** that **blocks** when absent/disabled; it does not degrade to a
  report-only pass.
- `teach`/`shape` are per-surface setup — don't re-run blindly; skip when context/direction exists.
- Headless runs never prompt — the `live` step and any offer take safe defaults (skip / block) and log it.
