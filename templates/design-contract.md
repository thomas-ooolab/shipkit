---
contract-for: NNN            # the spec this contract backs (specs/NNN-slug/)
ticket: AR-NNN
artifact: ""                 # the mockup source: image path | .html path | design URL
tier: ""                     # html | url | screenshot
fidelity: ""                 # exact (computed styles) | low (screenshot-estimated)
palette: ""                  # project | default (which token set values snapped to)
reference: ""                # design-contract.reference.png | <image path>
captured: ""                 # e.g. "desktop 1280, tablet 768, mobile 375; states: hover, focus"
---

# Design Contract — {Feature / Surface}

**Produced by `/design-recon` from {artifact}. Consumed by the implementer (styling brief) and
`/design-verify` (fidelity gate).** Values are the project's Tailwind classes; a raw `(px/#hex)` in
parentheses means the snap was inexact (`exact:false`) or vision-estimated (`approx`) — double-check those.

> **Rule — match, don't reinterpret.** Implement with the classes below. Where a class is given, use
> *that* class; don't substitute a "close enough" value. `/design-verify` diffs the built UI against
> this file and blocks on class-level mismatches.
>
> **Rule — RESPONSIVE IS MANDATORY.** Every region MUST behave per its Responsive row at all three
> breakpoints (mobile 375 · tablet 768 · desktop 1280). No horizontal overflow, no fixed widths that
> exceed the viewport, stack/reflow as specified. A build that matches desktop but breaks at 375px is a
> **failure**, not a nitpick — this is enforced, not advisory.

## Tokens by region
<!-- One block per meaningful region (header, card, primary button, input …). Omit rows that don't
     apply. Prefer the Tailwind class; keep raw px/hex only when inexact/approx. -->

### {Region name} — `{selector or role}`
- **Layout:** {display + direction} · justify {…} · items {…} · **gap** {gap-N}
- **Padding / Margin:** {p-… / m-… per side, or shorthand}
- **Typography:** {text-N} {font-N} {family} · leading {…} · tracking {…} · color {text-token}
- **Surface:** bg {bg-token} · radius {rounded-N} · border {width + border-token} · shadow {shadow-… or raw}
- **States:** hover {delta, e.g. bg-blue-700} · focus {delta, e.g. ring-2 ring-blue-500} · active/disabled {…}
- **Responsive:**  *(REQUIRED for every region)*
  - **mobile (375):** {stack to flex-col · full-width · text-sm · hidden … — or "same as desktop"}
  - **tablet (768):** {deltas, or "same as desktop"}
  - **desktop (1280):** {baseline}

## Assets
<!-- Icons/SVGs (inline markup or name), images (URL / dimensions). "None" if none. -->
- {icon/image → source}

## Behavior notes
<!-- Non-token behavior the mockup implied: transitions/animation, conditional rendering, empty/loading
     states, focus order. "None observed" if the artifact showed none (common for screenshot tier). -->
- {behavior}

## Open questions
<!-- What this artifact could NOT determine — screenshot tier: dynamic states, exact hex, responsive
     behavior; any region the extraction truncated. Resolve before or during implementation. -->
- [ ] {gap the capture couldn't resolve}
