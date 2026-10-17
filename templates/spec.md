---
spec-id: NNN
ticket: AR-NNN
reporter_account_id: ""   # Jira accountId of the ticket's reporter (the PO) — /clarify tags this person
services: []          # submodule names from .shipkit/config.yml (auto-discovered + confirmed)
scope: ""            # e.g. fe-only | be-only | fe+be | ... — whatever the submodule set makes meaningful
tier: ""             # trivial | small | medium | large | unknown
status: draft        # draft | planned | in-progress | shipped
---

# {Feature Title}

**Ticket:** [AR-NNN]({jira-base}/browse/AR-NNN) · **Scope:** {scope} · **Tier:** {tier} · **Spec:** {NNN}

<!-- Every field below must trace to a cited source — (from ticket: "…"), (from comment by X: "…"),
     (from linked AR-NNN: "…"), (from attachment: "…"), (user confirmed: "…") — or be marked
     [not specified — ask before implementing]. Never synthesize requirements from general knowledge. -->

## Goal
<!-- 1–2 sentences. What outcome ships and why. Cite the source. -->

## Requirements
<!-- One atomic, testable REQ per acceptance criterion. Each cites its source. -->
- **REQ-001** — {single observable assertion} *(source: "…")*
- **REQ-002** — {single observable assertion} *(source: "…")*

## Key decisions
<!-- Confirmed structural choices: where the change lives, what it scopes, which component owns it.
     Restate verbatim. Mark any unresolved fork [not specified — ask before implementing]. -->
- **{decision}**: {choice} (user confirmed)

## Plan
<!-- Filled by /plan-deep. Approach per affected submodule; keep it short until then. -->
- **{submodule-a}:** {approach — layers, files, and the conventions its CLAUDE.md states}
- **{submodule-b}:** {approach} — {⚠️ staging-only, if `.shipkit/config.yml` says so}

## Contracts
<!-- Only if a cross-service interface changes. Otherwise "None". -->
- {new/changed endpoint, request/response shape, or shared type}

## Tasks
<!-- Filled/expanded by /plan-deep. Per submodule, dependency-ordered, each task tagged with its target. -->
### {submodule-a}
- [ ] T001 [REQ-001] ({submodule-a}) {description} — `path/to/file`
### {submodule-b}
- [ ] T010 [REQ-002] ({submodule-b}) {description} — `path/to/file`

## Edge cases
| Case | Expected behavior |
|------|-------------------|
| {edge case} | {behavior} |

## Open questions
<!-- Residual/unresolved items. Record AskUserQuestion answers here as Q→A. -->
- [ ] {anything the ticket left ambiguous — resolve before implementing}
