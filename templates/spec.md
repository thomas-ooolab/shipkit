---
spec-id: NNN
ticket: AR-NNN
services: []          # ai-roleplay | ai-roleplay-be | ai-roleplay-voice (auto-discovered + confirmed)
scope: ""            # fe-only | be-only | fe+be | fe+be+voice | ...
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
<!-- Filled by /plan-deep. Approach per affected service; keep it short until then. -->
- **ai-roleplay (FE):** {BFF proxy only; pages/components/hooks; TanStack}
- **ai-roleplay-be (BE):** {OpenAPI-first: api/api.yml → `make gen` → domain → repo → handler}
- **ai-roleplay-voice:** {⚠️ staging-only}

## Contracts
<!-- Only if a cross-service interface changes. Otherwise "None". -->
- {new/changed endpoint, request/response shape, or shared type}

## Tasks
<!-- Filled/expanded by /plan-deep. Per service, dependency-ordered, each task tagged with its target. -->
### FE — ai-roleplay
- [ ] T001 [REQ-001] (ai-roleplay) {description} — `path/to/file`
### BE — ai-roleplay-be
- [ ] T010 [REQ-002] (ai-roleplay-be) {description} — `path/to/file`
### Voice — ai-roleplay-voice
- [ ] T020 [REQ-00N] (ai-roleplay-voice) ⚠️ staging-only — `path/to/file`

## Edge cases
| Case | Expected behavior |
|------|-------------------|
| {edge case} | {behavior} |

## Open questions
<!-- Residual/unresolved items. Record AskUserQuestion answers here as Q→A. -->
- [ ] {anything the ticket left ambiguous — resolve before implementing}
