# Agents that drive a browser — rules, load check, cleanup

Shared by `/verify`, `/design-recon`, `/assign`, `/bugfix`, `/run-pipeline` and `/spec-from-ticket`. **Stopping an agent (`TaskStop`) does not
stop the processes it started.** A browser-driving agent that wrote a chain of shell loops (`chain.sh` → `tail.sh` → `rerun.sh`) left them
relaunching `node run.cjs`, each run opening a `chrome-headless-shell` with 3–5 child processes: load average 151, eight loops to kill by hand.

## The rules — paste this block into the brief of every agent that drives a browser from a script

> **Browser rules (REQUIRED).** (a) Run everything in the foreground, with a timeout, one script after another, one browser at a time.
> (b) No background orchestration: no `nohup`, no `&`, no `while` / `until` / `watch` loop, no script that starts another script (chain,
> tail, all, rerun). Each script runs once and exits. (c) Close the browser in a `finally` (`await browser.close()`), and label the run:
> `SHIPKIT_RUN=<ticket>-<region>` in the environment, and your own scratch directory `<scratch>/<ticket>-<region>/` as the working
> directory of every script and as its `userDataDir`. (d) Before your final answer run
> `bash "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-browsers.sh" <that scratch directory>` and leave no node or chromium process behind.
> (e) Playwright runs headless: `chromium.launch({ headless: true })` in a script, a server started with `--headless` for the MCP tools.

The Playwright MCP browser tools (`browser_*`) are owned by their MCP server; the rules above are for scripts an agent writes and runs itself,
except (e), which also decides how that server is started. The one visible window is `scripts/capture-native-popup.js` (a native popup has
no headless form), and the user's own Chrome (`--extension`, claude-in-chrome) is not Playwright's browser.

## After the agent ends or is stopped — the coordinator's job
When an agent that drove a browser finishes, fails or is stopped by the coordinator (`TaskStop`), run
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-browsers.sh" <that agent's scratch directory>` and report what it killed (or `nothing to clean`).
`--dry-run` only lists. The script touches only processes whose working directory or command line is under that directory, and the
orphaned `chrome-headless-shell` of ms-playwright: never the user's Chrome, never the Playwright MCP browser, never anything else.

## Before starting several browser agents
Read `uptime` (and `sysctl -n hw.ncpu`). **Default: one browser agent at a time**, the next starts when the previous has ended and been
cleaned up. Run two or more in parallel only when the 1-minute load average is below half the CPU count **and** the user agrees; write the
reason in each brief ("load 3.1 on 12 cores, user agreed to 2 in parallel").

| Excuse | Reality |
|---|---|
| "A chain script lets the three regions run unattended" | Nobody is there to stop it. One script, one run, exit; the agent waits for it in the foreground. |
| "The agent is stopped, so its browsers are gone" | Stopping an agent does not stop its children. Run the cleanup on its scratch directory. |
| "Two verifiers in parallel are faster" | On a loaded machine they are slower and can freeze it. Check `uptime`; default is one. |
