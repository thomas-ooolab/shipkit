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
**Reaching a state.** A state the contract or the design shows (a low-confidence or disputed badge, a pill, an empty list…) that the local
data does not have is reached, not skipped, the way `SKILL.md` builds a missing variant (*Variant matrix*): use what the product already
offers (another record, a role, a flag, a URL), else seed it (on a local target without asking, elsewhere ask). Only when the state is one API response that cannot be
produced for real, or the user declines seeding, may that response be patched in the page (e.g. Playwright `page.route`; never a database
write); the report then marks the state `simulated`, because a fake response can hide a state the backend never produces. A state reached
by none of these is `UNVERIFIED`: the gate is `INCOMPLETE`, never `PASS`.
`browser_take_screenshot` at each breakpoint for the report + perceptual fallback.

### A2 — Diff against the contract
Match built regions to contract regions by selector/role/text, then diff per token.

**`fidelity: exact` (html/url contract) — every computed-style delta is `blocking`.** Compare the computed values, not the snapped
Tailwind class: font size, weight, leading, tracking, color (exact rgb), padding, margin, gap, radius, border, shadow, width, height. The
tolerance is **0.5 px** for rounding and nothing else. Two colors that snap to the same token but differ in rgb (`#00a63e` vs `#16a34a`)
are different colors. A delta is never `advisory` because it is "the same class", "under one class step" or "only leading/tracking":
`advisory` exists only for `fidelity: low`.
- **Layout:** display/direction/justify/align mismatch → `blocking`.
- **State:** a hover/focus delta present in the contract but absent in the build → `blocking`
  (behavior, not just looks).

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

### A3 — 1-to-1 against the running design (REQUIRED when the contract's `artifact:` is an html file or a url, or the design can be served)
The contract lists only the regions and tokens recon chose; this step catches what it left out.
1. Open the design next to the build: an html artifact is served as in `/design-recon` Step 4a (`recon.sh serve`, stopped afterwards), a
   url is navigated. Same viewport (1280, 768, 375), same persona and same state as the build — reached as in A1 where local data lacks it.
2. Extract **every** element of the region in both (`recon-extract.js` on the region root, not only the nodes the contract lists) and diff
   structurally: the element list first (tag/role/text, in order), then each element's computed style by the A2 rule. An element on one
   side only → `blocking`.
3. Static UI text — titles, labels, buttons, placeholders, empty states — matches the design **verbatim**, capitalisation and punctuation
   included. Data content (names, numbers, dates) is compared by style only.
4. Save, per breakpoint, the design/built screenshot pair and a pixel diff under `.shipkit/evidence/<TICKET>/`. They are secondary
   evidence: an area the diff lights up that the element diff passed is investigated, never waved through.
A contract with no servable artifact (screenshot tier) skips A3, and the report says so.

If the measuring or diffing is delegated to an agent, its brief carries A2's rule and this step verbatim. It never says "keep it
proportionate", "group tokens per region" or "same class, so advisory" for `fidelity: exact`. The brief also carries the *Browser rules*
block of `${CLAUDE_PLUGIN_ROOT}/references/browser-agents.md`, and when that agent ends or is stopped you run
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-browsers.sh" <its scratch directory>`: stopping an agent does not stop its browsers.

| Excuse | Reality |
|---|---|
| "Same Tailwind class, so it's advisory" | Not under `exact`: the computed values differ and the user sees the difference. `advisory` is for `fidelity: low`. |
| "The contract doesn't list that element" | The contract is what recon chose to write down. A3 compares the whole region. |
| "Local data has no such state, skip it" | Reach it (A1). A state that cannot be measured is `UNVERIFIED`, and the gate is `INCOMPLETE`, never `PASS`. |
