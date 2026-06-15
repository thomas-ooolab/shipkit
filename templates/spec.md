---
spec-id: NNN
ticket: AR-NNN
services: []          # ai-roleplay | ai-roleplay-be | ai-roleplay-voice
scope: ""            # fe-only | be-only | fe+be | fe+be+voice | ...
status: draft        # draft | in-progress | shipped
---

# {Feature Title}

**Ticket:** [AR-NNN]({jira-base}/browse/AR-NNN) · **Scope:** {scope} · **Spec:** {NNN}

## Goal
<!-- 1–2 sentences. What outcome ships and why. -->

## Requirements
<!-- One REQ per acceptance criterion. Each task below cites a REQ-ID. -->
- **REQ-001** — {requirement}. *AC:* Given … When … Then …
- **REQ-002** — {requirement}. *AC:* Given … When … Then …

## Plan
<!-- Technical approach per affected service. Keep it short. -->
- **ai-roleplay (FE):** {approach — pages/components/hooks; BFF proxy only, no business logic}
- **ai-roleplay-be (BE):** {OpenAPI-first: api/api.yml → `make gen` → domain → repo → handler}
- **ai-roleplay-voice:** {⚠️ staging-only until production-ready}

## Contracts
<!-- Only if a cross-service interface changes. Otherwise write "None". -->
- {new/changed endpoint, request/response shape, or shared type}

## Tasks
### FE — ai-roleplay
- [ ] T001 [REQ-001] {description} — `path/to/file`

### BE — ai-roleplay-be
- [ ] T010 [REQ-002] {description} — `path/to/file`

### Voice — ai-roleplay-voice
- [ ] T020 [REQ-00N] ⚠️ staging-only — `path/to/file`

## Edge cases
| Case | Expected behavior |
|------|-------------------|
| {edge case} | {behavior} |

## Open questions
- [ ] {anything the ticket left ambiguous — resolve before implementing}
