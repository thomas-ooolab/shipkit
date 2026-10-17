# /verify — Step 2: which browser tool, evidence images, native popups, local login

> Loaded by SKILL.md before the first FE check or Part A run.

### Browser tool — Playwright first, claude-in-chrome only when it must be the user's Chrome
- **Default: Playwright MCP in its isolated mode** (`browser_*`, server run as `npx @playwright/mcp@latest
  --isolated` — tools named `mcp__playwright__browser_*`). It is its own browser with its own empty, in-memory
  profile and never touches the user's tabs or sessions. Use it for every FE check on a local/dev/staging app with
  a test account: read the DOM (`browser_evaluate`, e.g. list a select's options), `browser_take_screenshot`, drive
  the flow. **Not every Playwright MCP is isolated:** one started with `--extension` (the `ecc` plugin's
  `mcp__plugin_ecc_playwright__*` is) attaches to the user's real Chrome — same risks as claude-in-chrome below.
  Prefer the isolated server; if only the `--extension` one is connected, say so and get the user's yes first. Not
  installed → `claude mcp add --scope user playwright -- npx @playwright/mcp@latest --isolated`, then a new session.
- **claude-in-chrome only when the user's real Chrome is required:** the page opens only for a logged-in user
  (an auth-walled design link in `/design-recon`, SSO, an extension) or needs the user's own session or cookies.
  Say these risks to the user first: the window also holds their other tabs and bookmarks (private data can leak
  into a read or a screenshot); Chrome autofills their real accounts into login forms; the agent's tab runs in the
  background, not the one on screen; it cannot type a password except a test account the user typed in chat or
  one you seeded for a localhost app. **Tell the user before bringing Chrome to the foreground** — it takes over
  their screen.
- **Evidence images come only from the browser tool** (`browser_take_screenshot` or the extension's screenshot).
  Never a full-screen `screencapture`, or `-R` on any region that isn't a window you opened yourself, nor any
  other image the browser tool did not produce: it captures whatever sits on top of the screen, other windows and
  personal documents included. The one exception is the script below. Playwright MCP writes
  relative to the repo root, so pass `filename` as `.shipkit/evidence/<TICKET>/<id>-<slug>-after.png`, or the
  image (and a `.playwright-mcp/` log folder) lands in the repo — never commit that folder. Open every image (Read)
  before it is attached; one showing anything outside the app is deleted, not attached.
- **A state the browser tool can't capture** (anything the browser draws outside the page: a native `<select>`
  popup, a date picker — headless has no window, and an extension click doesn't open it). Always put what the
  page's own state says (e.g. a select's options, read from the DOM) in the evidence `.txt`. For an image on
  macOS run `node "${CLAUDE_PLUGIN_ROOT}/scripts/capture-native-popup.js" --fe <FE dir with node_modules/playwright>
  --setup <login+goto module> --click <css> --out <png>`: a visible Chromium whose Playwright click opens the
  popup; it captures that window by id and the popup by `-R` on its own layer-101 rectangle (the only `-R`
  allowed), and composites them. Header of the script has the details; it needs Screen Recording permission and
  the window on the visible display, so tell the user a Chromium window will appear. Where that can't run, render
  the same content where the tool can capture it (e.g. `browser_evaluate` setting `select.size = <option count>`)
  and caption it as altered ("list shown expanded"). Don't try any other capture.
- **Local login: seed a dedicated test user** rather than using an account from a Jira comment — only on the
  user's yes, only in the local DB. Insert the user + membership rows with `psql -tAq` (with `RETURNING`, take
  the first line: it also prints `INSERT 0 1`); password random from Python `secrets`, hash
  `htpasswd -bnBC 10 x <pw> | cut -d: -f2` with the `$2y$` prefix changed to `$2a$` (the BE's bcrypt accepts it);
  keep the password in a `0600` file in the scratchpad and never print it in chat.
