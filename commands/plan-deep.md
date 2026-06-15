---
description: Deepen the Plan and Tasks sections of an existing spec for a ticket — expand technical approach, add Targets (which submodule each task belongs to), and dependency-order the tasks. Use when a feature is non-trivial and the lean plan needs more detail before implementing.
argument-hint: "--ticket <jira-ticket>  (e.g. --ticket AR-123)"
---

# shipkit · plan-deep

Read `.shipkit/config.yml`. Locate the spec for the ticket in `$ARGUMENTS`
(`<spec.dir>/NNN-{slug}/spec.md`). If none exists, run `/spec-from-ticket {ticket}` first.

Expand **only** the `## Plan` and `## Tasks` sections of that one `spec.md` — do not split into
new files. Keep everything in the single spec file (shipkit stays one-file).

Do:
1. **Plan** — per affected service, detail the technical approach, key files/layers, and the
   order of operations. BE: confirm OpenAPI-first (`api/api.yml` → `make gen` → domain → repo →
   handler). FE: BFF proxy + TanStack hook placement. Voice: staging-only constraint.
2. **Tasks** — make each task carry an explicit **target** (which submodule) so PRs can fan out:
   `- [ ] T001 [REQ-001] (ai-roleplay-be) {desc} — path`. Dependency-order them
   (types → contract → repo → handler → UI → test). Every task cites a `REQ-NNN`.
3. Note cross-service ordering (e.g. "BE endpoint must merge before FE hook").

This `Targets:`-per-task structure is what `/pr-from-plan` reads to open one child PR per
submodule, and what `/bump-submodule` uses after they merge.

Report: tasks per target and any cross-service merge-order constraints.
