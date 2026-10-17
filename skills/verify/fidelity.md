# /verify — Part A: UI fidelity (design contract diff)

> Loaded by SKILL.md only when a `design-contract.md` exists. Step numbers (A1, A2, Step 4) are the ones SKILL.md refers to.

## Part A — UI fidelity (only when a design contract exists)

### Step 4 — Measure and diff against the contract
Needs the Part A route from Step 1. Everything below is the unchanged fidelity method.

### A1 — Measure the built UI (same method as recon)
`browser_navigate` to the route. For each breakpoint the contract records (**always** desktop 1280 +
tablet 768 + mobile 375 — responsive is mandatory, never skipped):
1. `browser_resize` to the width.
2. Seed `window.__SHIPKIT_OPTS` (same `rootSelector` + project `colors`, via `recon.sh tailwind-config`),
   then `browser_evaluate` the contents of `${CLAUDE_PLUGIN_ROOT}/scripts/recon-extract.js`.
3. Record `document.documentElement.scrollWidth > window.innerWidth` → **horizontal overflow** flag.
For each state the contract records (hover/focus/active), drive it and re-extract that node.
`browser_take_screenshot` at each breakpoint for the report + perceptual fallback.

### A2 — Diff against the contract
Match built regions to contract regions by selector/role/text, then diff per token.

**`fidelity: exact` (html/url contract) — numeric diff.** Per token, compare and apply tolerance:
- **Spacing / radius / font-size:** mismatch if the snapped **Tailwind class differs** (e.g. contract
  `gap-4`, built `gap-3`). A sub-class px delta on an inexact value is `advisory`, not `blocking`.
- **Color:** mismatch if the snapped token differs (`bg-blue-600` vs `bg-blue-500`) → `blocking`.
- **Typography:** family / weight / size / leading mismatch → `blocking` for size+weight, `advisory`
  for leading/tracking.
- **Layout:** display/direction/justify/align mismatch → `blocking`.
- **State:** a hover/focus delta present in the contract but absent in the build → `blocking`
  (behavior, not just looks — the class of bug the user flagged).

**`fidelity: low` (screenshot contract) — perceptual diff.** No numeric target exists, so compare the
built screenshot to the reference image **per breakpoint** via vision: report structural/spacing/color
deltas as `advisory` (the contract itself was approximate), but keep the responsive checks below
`blocking` — those are measured on the live DOM, not the image, so they're exact regardless of tier.

**Responsive gate (ALL tiers, always `blocking`)** — this is the rule the implementer keeps skipping:
- **Horizontal overflow** at any breakpoint (`scrollWidth > innerWidth`) → FAIL.
- **Non-stacking:** a row that the contract marks as stacking on mobile still `flex-row` at 375 → FAIL.
- **Fixed widths that overflow the viewport** (element `box.w` > breakpoint width) → FAIL.
- **Text clipping / truncation** not present in the contract at a breakpoint → FAIL.
A UI can match desktop pixel-for-pixel and still FAIL here — that's intended.
