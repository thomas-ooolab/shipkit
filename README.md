# shipkit

**Lightweight spec-driven development for Claude Code.**
One ticket, one guard-railed pipeline — from a lean one-file spec to merged PRs across submodules.

shipkit is the lighter successor to speckit. Instead of 9 commands generating 5–9 files per
feature, shipkit gives you **one everyday command** and **one spec file per feature**. Install it
once; no `.specify/` scripts or templates to copy into each repo.

---

## Why shipkit, not speckit?

**The problem.** We adopted speckit for spec-driven development, but it was too heavy for day-to-day
work:

- **Too many artifacts.** Every feature spawned 5–9 files (`spec.md`, `requirements.md`, `plan.md`,
  `contracts.md`, `tasks-*.md`, `research.md`, `data-model.md`, checklists…). Most got skimmed once
  and went stale — more to write and maintain than to read.
- **Too many commands.** Nine `/speckit.*` steps to drive a single feature through.
- **Manual, per-repo install.** speckit isn't a plugin — every project needed its `.specify/` scripts,
  templates, and all nine command files copied in by hand and kept in sync. Onboarding a new repo (or
  a new teammate) meant repeating that setup; a fix to one command had to be re-copied everywhere.
- **Shallow plans.** speckit's `plan.md` was largely a template fill — it didn't read the real code, so
  paths and symbols were often guessed and went stale.
- **Not built for our shape.** speckit assumes a single repo; our platform is a **multi-submodule**
  layout (BE + web FEs + mobile) coordinated from an orchestration root, on **Bitbucket + Jira**, not
  GitHub.

**What shipkit changes.**

- **One file per feature** — `specs/NNN-slug/spec.md` holds goal · requirements · plan · tasks ·
  contracts · edge cases. Spec lives in git (diffable, reviewable, traceable), not buried in Jira.
- **One everyday command** — `/run-pipeline <ticket>` drives the whole flow; the stage skills exist
  for when you want a single step.
- **Installs in seconds** — it's a Claude Code plugin: two commands (`/plugin marketplace add` +
  `/plugin install`) and the whole team has every skill. Updates are one `marketplace update`; fixes
  ship to everyone at once. No scripts or command files copied per repo — `/bootstrap` then writes a
  single `.shipkit/config.yml` per project.
- **Deeper, verified planning** — `/plan-deep` grounds in the **real submodule code** via an Explore
  agent, then runs parallel reviewer agents that **verify every file path and symbol exists** and
  catch missed edge cases / cross-submodule ordering *before* the plan is written. speckit's plan was
  a template fill; shipkit's is grounded and checked.
- **Built for our shape** — auto-detects which **submodules** a ticket touches (by grepping the code),
  fans out one PR per submodule + a parent PR, and bumps submodule refs — all on **Bitbucket**, with
  state tracked in **Jira** (no GitHub labels/auto-close).
- **Same SDD discipline, kept** — grounded + agent-verified plans, three-pass review, allowlist-gated
  PRs. Lighter artifacts, not a lighter process.
- **One standard across the company** — the same skills, the same one-file spec shape, and the same
  ticket → spec → plan → review → PR → bump pipeline in **every** repo.
  Specs and reviews look the same everywhere, onboarding a project or a teammate is "install the
  plugin," and an improvement to the workflow ships to every team at once. It **auto-detects** whether
  a repo is a plain **single repo** or a **submodule orchestration root** and adapts the flow
  accordingly — so the same plugin is the standard for *every* repo, not just submodule roots.

(Full side-by-side in [What's different from speckit](#whats-different-from-speckit) below.)

---

## Install

```bash
# in Claude Code
/plugin marketplace add thomas-ooolab/shipkit
/plugin install shipkit@shipkit
```

Public GitHub repo — no credentials needed to install or auto-update. If you'd rather pin the
git URL explicitly: `/plugin marketplace add https://github.com/thomas-ooolab/shipkit.git`.

### Kiro (Agent Plugins)

The root `plugin.json` follows the [Agent Plugins 1.0.0](https://agent-plugins.org) manifest, so Kiro
can install shipkit as a power. The standard only carries `skills/` and `mcp.json`, so in Kiro:
`agents/` (the reviewer subagents) and Claude hooks are not loaded, and `${CLAUDE_PLUGIN_ROOT}` /
`` !`cmd` `` in a SKILL.md are Claude Code features the spec does not define, so skills that call
`scripts/probe.sh` need those paths adjusted. Keep `plugin.json` and `.claude-plugin/plugin.json`
versions in sync when bumping.

---

## Day-to-day

```bash
/fix-permissions           # ONCE per repo — allow shipkit's read-only probe (see Permissions)
/bootstrap                 # once per project — writes .shipkit/config.yml
/run-pipeline AR-123       # every ticket — the whole pipeline in one command
```

`/run-pipeline` fetches the Jira ticket, detects which submodules are affected, creates the
branches, and writes **one** lean `specs/NNN-slug/spec.md` (goal · requirements · plan · tasks ·
contracts · edge cases). Then you implement, review, and open PRs.

---

## The pipeline

```
/run-pipeline AR-123       (re-derives state from git / Bitbucket / Jira, runs what is pending, stops at each gate)
      │
/spec-from-ticket          ticket → one lean spec.md  (+ /cross-check against other tickets, specs, code)
      ▼
/clarify                   GATE — open PO questions go to Jira and are polled until answered
      ▼
/plan-deep                 grounded, reference-verified plan + per-submodule tasks into spec.md
      ▼
/assign  (or by hand)      GATE — implement; /assign fans the tasks out to parallel agents, per submodule
      ▼
/verify  +  /review-changes   prove it on the running app (evidence) · three-pass review + drift check
      ▼
/pr                        one child PR per submodule + parent PR → ping reviewer, triage until sign-off
      ▼
/merge AR-123              GATE — merge signed-off child PRs → wait on the Bitbucket pipeline (twg) → bump and
                           merge the root PR → move the Jira ticket
      ▼
/bump-submodule path@sha --closes AR-123    only after a by-hand merge (the same bump /merge does)
```

### Bug-fix pipeline

A reported defect takes a shorter flow — no new spec, no PO question round, no `/plan-deep` (`/bugfix` edits `spec.md` in place when the fix changes it): `/run-pipeline AR-123 --bug` (what `/developer`
starts for a bug). Its fix goes on a `fix/AR-123-<slug>` branch cut from the target when the old worktree's code is already
merged; an unmerged branch (or a merged one that still has uncommitted changes or an open PR) is reused.

```
/bugfix AR-123 [<comment-id>]    triage each concern, fix real defects (regression test first, via /assign --agent kiro), prove each with /verify
      ▼
/verify  +  /review-changes      /verify --req <changed REQs>, only when the fix changed spec.md
      ▼
/pr
      ▼
/merge AR-123                    GATE — as in the standard flow
      ▼
/bump-submodule path@sha --closes AR-123    only after a by-hand merge
```

## Skills

Each is a plugin **skill** (`skills/<name>/SKILL.md`) — invoke explicitly with `/name`, or let Claude
auto-trigger it by description.

| Skill | Role |
|---|---|
| `/shipkit:help [<use case>]` | **Lost? Start here** — prints the installed shipkit version and drafts step-by-step instructions (which skills, in what order, your ticket filled in, prerequisites, where you must approve) for a use case; `/shipkit:help <skill>` shows one skill. Read-only. |
| `/fix-permissions` | One-time per-repo — allow the read-only probe so injected context can run |
| `/bootstrap` | One-time per-project setup → `.shipkit/config.yml` |
| `/run-pipeline <ticket> [--bug]` | **Everyday skill** — ticket → scope → branches → one lean spec; `--bug` runs the shorter bug-fix flow (`/bugfix` → verify if the spec changed → review → PR → merge) |
| `/spec-from-ticket <ticket>` | Just write the spec (no branches) |
| `/clarify <ticket>` | Sends the spec's open business questions to the PO in one Jira comment (real @mention, your approval before every post) and waits for the reply in a background poller until every question is resolved. Called right after `/spec-from-ticket`. |
| `/bugfix <ticket> [<comment-id>] [--agent kiro]` | A tester's Jira comment reports a bug: traces each concern to the code, fixes real defects (regression test first, proved with `/verify`), explains what is by design, asks the PO about product decisions, and keeps checking Jira until the reporter confirms. |
| `/plan-deep --ticket <ticket>` | Verified, grounded plan into `spec.md` — Explore-agent grounding + parallel self-review & reference-verify, per-task submodule targets |
| `/assign <ticket \| task> [--only <submodule,...>]` | Fan out `spec.md`'s per-submodule tasks to parallel background agents instead of implementing submodules one at a time — dependency waves per the plan's Part order, ground-truth skip on already-in-progress branches. Inside an Orca-managed worktree each agent runs as a visible Orca terminal (see `/orca-cli`); otherwise as a background `Agent`. Workers only commit and never push; `/assign` pushes a branch only after it has read the commit and accepts it (`--no-push` leaves the push to the caller). Hands off to `/pr` afterward. |
| `/design-recon <artifact> [--ticket <t>]` | **Match a mockup** — drives a screenshot / HTML / auth-gated Claude design link in a real browser (Playwright MCP), reads *computed* styles, snaps to the project's Tailwind tokens, and writes `design-contract.md` (all breakpoints + states). Cheaper *and* more accurate than reading the mockup's HTML. |
| `/verify [--ticket <t>] [--concern "<scenario>"] [--url <route>] [--api <url>]` | **Prove it works** after a feature is implemented or a bug fixed — exercises every `REQ-NNN` (or `--concern`) on the running app and saves evidence under `.shipkit/evidence/<ticket>/`: **FE → screenshot, BE → request/response + data** (redacted; no evidence = no PASS). When a `design-contract.md` exists it also renders the *built* UI at every breakpoint and diffs computed styles against it (responsive breakage fails). Gates `PASS` / `FAILED` / `INCOMPLETE`; feature runs only draft the evidence comment locally — `/merge` posts it to Jira (after you approve) right before it moves the ticket's status; `/bugfix` runs don't. Replaces `/design-verify`. |
| `/cross-check <ticket> [--stage spec\|plan\|post]` | Finds contradictions between a ticket and other Jira tickets, earlier specs, the ticket's own edge cases and the running code (who may see/do what, thresholds, limits, states, notifications, existing features; every route that touches the entity). Writes `cross-check.md` + `[ticket-conflict]` PO questions with verbatim quotes and a highlighted Jira screenshot (Chrome, text-only fallback). Never picks a winner. Called by `/spec-from-ticket` (Step 5b) and `/plan-deep`; `/clarify` sends the questions. `--stage post` reconciles a point raised in a discussion with QC, PO or others (tester comment, bug report, PO answer, later dated decision) — not a step after implementing: rule inventory, consumer × role matrix, dated PO-decision conflicts, draft PO questions, verdict ship / fix first / ask PO. Read-only (post: also runs the app). |
| `/review-changes [--ticket <t>] [--pr <id>]` | Three-pass parallel review (correctness/security · style/docs · infra/ops) across affected submodules + drift check. Local mode prints findings; PR mode posts a locked Bitbucket comment. |
| `/pr <ticket> [--implement] [--target staging\|main]` | Two phases, in order. **Open:** fan out child PRs per submodule + parent PR (allowlist-enforced, test-gated, reuses already-open PRs); opt-in `--implement` writes the code via parallel background agents first. **Review loop:** pings the Slack reviewer and triages every concern (fix / escalate to Jira / explain) until sign-off. Never merges. |
| `/developer [<slack-thread-url>] [--auto]` | **No URL → observer:** watches your Slack notifications (@mentions, DMs, replies in threads you joined, QC report posts that name a ticket, and **every other top-level post by someone else in every channel you are in** — reported in one line, never dropped; realtime only, nothing sent before it starts is replayed) via `observe-slack.js` + Monitor and *drafts* answers for you to approve; `--auto` (or a scope you state, e.g. "auto-send in #qc") posts directly. **With URL:** reads one Slack thread and replies **as you, the developer** (user token via `post-slack.js`, which can attach files/images; like `/pr`), in the thread starter's language. Answers only what it verified in the code / live Jira ticket, otherwise "let me check"; never commits you to dates, refunds or access. Watches the thread until the asker is done: pushed by Slack Socket Mode (`wait-for-slack-event.js`, needs `SLACK_APP_TOKEN` — see *Slack push setup*) or, without it, polled by `wait-for-slack-reply.sh`. Read-only on code, git and Jira. Needs `SLACK_REVIEW_TOKEN`. |
| `/merge <ticket>` | Merges child PRs already signed off with no git-detected conflict (no PR CI is read — these repos only run deploy pipelines after the merge; prints its plan and warns that the merge triggers the deploy, then goes ahead unless something is off — missing sign-off, conflict, failed pipeline, a root rebase/force-push, a rejection; the Jira status and QC come from your recent tickets, not prompts), waits on each merge's Bitbucket Pipeline via bundled `wait-pipelines.sh` (matched by merge sha). If all SUCCESSFUL: bumps the root PR's pointers, rebases gitlink-only conflicts, merges it (confirms again), then moves the Jira ticket to `jira.after_merge_transition` (unset → **asks which transition**, from the ticket's real ones, and offers to save it; never silently skipped) and **asks who the QC is** (picked from the ticket's assignable users; `jira.qc_account_id` is only the suggested default). |
| `/bump-submodule <path>@<sha> --closes <ticket>` | Verify merged SHAs, bump submodule refs (rebase-safe), update/open the parent PR with a Bumps table. Never writes to Jira — the report always says which ticket you move to Done yourself |

## Slack push setup (optional, for `/developer`)

Without it `/developer` polls the thread every 15s. With it, Slack pushes new replies over a websocket — no
polling, no public URL, no bot to invite into each channel. One-time:

1. <https://api.slack.com/apps> → **Create New App → From a manifest** → pick the workspace → paste
   `templates/slack-app-manifest.json` (user scopes, user events and Socket Mode are all in it).
2. **Install App → Install to Workspace** → copy the **User OAuth Token** (`xoxp-…`) → `export SLACK_REVIEW_TOKEN=…`.
3. **Basic Information → App-Level Tokens → Generate Token** with scope `connections:write` → copy the
   `xapp-…` token → `export SLACK_APP_TOKEN=…`.
4. Node ≥ 22 on the machine running Claude Code (built-in `WebSocket`; no `npm install`).

| Env var | Token | Scopes / events it needs | Used by |
|---|---|---|---|
| `SLACK_REVIEW_TOKEN` | user token `xoxp-…` | user scopes `chat:write` (post as you), `files:write` (attach files/images to a reply; an app installed before this scope existed must be re-installed), `channels:history`, `groups:history`, `im:history`, `mpim:history` (read threads) | `/developer` (post, read thread, `auth.test`), `/pr` Slack phase |
| `SLACK_APP_TOKEN` | app-level `xapp-…` | `connections:write`; user events `message.channels`, `message.groups`, `message.im`, `message.mpim` | `/developer` push waiter and observer (Socket Mode) |

No bot token, client id/secret or signing secret is used. **Leave token rotation off** (Basic Information →
App-Level Tokens, and OAuth & Permissions): the scripts read each token once from the environment and
cannot refresh it, so a rotating token dies after 12h — and rotation can't be turned off once it's on.

Events arrive for every channel you are in. `wait-for-slack-event.js` (URL mode) keeps only the watched
thread; `observe-slack.js` (no URL) keeps @mentions, DMs, replies in threads you joined, top-level channel posts by people that name a ticket (QC reports) and every other top-level post by people (`channel`), and prints ids
only — never message text. Both drop your own messages. Slack allows ~10 concurrent socket connections per
app: one per watched thread in URL mode, one in total for the observer. Observer gaps: messages posted
while the socket reconnects (~2s) are not replayed. Check the scripts without Slack:
`node scripts/wait-for-slack-event.js --self-test`, `node skills/developer/observe-slack.js --self-test`,
`node scripts/post-slack.js --self-test`. `post-slack.js` also edits a message you already posted:
`node scripts/post-slack.js edit <channel_id> <ts> < new-text` (`chat.update`; same `chat:write` scope, your own
messages only, text only — attachments stay).

## Design fidelity loop (UI tickets with a mockup)

FE implementations drift from the design — wrong spacing/color, missing hover states, and (chronically)
**desktop-only layouts that break on mobile**. And reading a mockup's HTML to avoid that is both
expensive and unreliable (utility classes, CSS variables, and the cascade mean authored CSS ≠ what
renders). shipkit closes this with a measure-based loop:

```
/design-recon <mockup> --ticket AR-123     ← Half 1: open the mockup in a real browser (Playwright MCP),
      │                                       read COMPUTED styles, snap to the project's Tailwind tokens,
      │                                       write specs/NNN/design-contract.md (all breakpoints + states)
      ▼
   implement — the contract IS the styling brief (assemble known classes, not guesses)
      ▼
/verify --ticket AR-123 --url <route>   ← Half 2: render the BUILT UI at every breakpoint,
      │                                            diff computed styles vs the contract, gate PASS/FAILED
      ▼                                            with expected → actual → fix. Responsive breakage fails.
   fix → re-run until PASS → /review-changes → /pr
```

**Three artifact tiers**, auto-detected: an **HTML file** or **public URL** → exact computed-style
capture; a **screenshot** → honest vision-estimate (marked `approx`, verified perceptually). Same
extractor runs both halves, so a diff is a real build gap, not two measurement methods.

**Playwright MCP** drives the browser. Its own headless Chromium handles HTML + public URLs with **no
extension**. Only an **auth-gated Claude design link** needs the [Playwright Chrome extension](https://chromewebstore.google.com/detail/playwright-extension/mmlmfjhmonkocbjadbfplnigmagldckm)
so the MCP attaches to *your* Chrome and reuses your logged-in session. The skills degrade cleanly when
it's absent (they block with a clear message, never fake a pass).

> Responsive is enforced two ways: `/verify` fails on live overflow/non-stacking at 375/768/1280,
> and `/review-changes` statically flags desktop-only diffs (hardcoded widths, no `sm:`/`md:` variants)
> **even on tickets without a contract**.

`/run-pipeline` runs `/verify` as a gate for **every** ticket (behavior evidence: FE screenshot, BE data); a UI
ticket additionally asks once whether to run the design-fidelity half (recon→verify, remembered for resumes) —
opt in and recon runs after the spec and the built UI is diffed against the contract before PRs. `FAILED` and
`INCOMPLETE` halt like a review blocker; `auto` runs skip only the design-fidelity half.

## Permissions (run `/fix-permissions` first)

shipkit skills load context by auto-running `!`bash …/probe.sh …`` at invocation. Claude Code won't
run an **injected** shell command unless it's pre-authorized, and injected commands can't show the
interactive approval prompt — so without the allow-rule, `/bootstrap` fails with *"command requires
approval"*.

`/fix-permissions` resolves a bundled applier and **prints a terminal command for you to run** — a
command *you* run is your own action and bypasses the injection/classifier block, whereas a command
the model runs would hit the same wall. Run it **once** before `/bootstrap`:

```bash
bash "$(find ~/.claude/plugins -name apply-permissions.sh 2>/dev/null | sort -V | tail -1)" --user
```

`--user` writes `~/.claude/settings.json` — covers **every** repo at once, and is the scope a
`/pr --implement` **background worktree agent** reads. (`--project` writes the repo's
`.claude/settings.json` instead; commit it to share with the team.) The key rule is `Bash(bash:*)` —
the plugin lives at a versioned cache path, so a path-scoped rule would break on every update. The
applier is idempotent and backs up before writing. The rules are broad on purpose (`bash:*`, `python3:*`, `node:*`,
`curl:*` run any script of that kind without a prompt in the chosen scope) — pick `--project` to limit the grant to one repo.

## Bitbucket credentials

Skills that call the Bitbucket REST API (`/pr`, `/review-changes`, `/bump-submodule`, `/run-pipeline`,
`/spec-from-ticket`, `/merge`) read two variables: `BITBUCKET_USERNAME` and `BITBUCKET_APP_PASSWORD`. The second keeps its
old name but takes an **API token** (`BITBUCKET_API_TOKEN` is read when it is empty) (Atlassian account → Security → API tokens, with the pull-request and repository
scopes); with an API token `BITBUCKET_USERNAME` is your Atlassian account e-mail. Calls go through
`scripts/bitbucket-api.sh`, which hands the credentials to curl on stdin, never on its command line.

## Other tools some skills use

shipkit does not install these; a skill that needs one says so and stops when it is missing.

| Tool | Used by |
|---|---|
| `superpowers` plugin (`systematic-debugging`, `test-driven-development`) | `/bugfix`, `/pr` review loop |
| Orca CLI + `orca-cli` / `orchestration` skills, `kiro-cli` | `/assign` (Orca mode), `/developer` Start mode |
| `twg` CLI | `/merge` (pipeline wait), `/developer` (deploy status) |
| Playwright MCP, Claude in Chrome | `/verify`, `/design-recon`, `/cross-check` screenshots |
| `JIRA_*`, `SLACK_*`, `BITBUCKET_*` environment variables | see the sections on this page |

Optional per-project settings in `.shipkit/config.yml` (`language`, `timezone`, `observer_hours`, `git_ssh_rewrite`) are
listed in the template `/bootstrap` writes.

## Posting Jira comments

**Rule for every skill: write to Jira/Slack through this plugin's scripts (`scripts/jira-comment.py`, `scripts/post-slack.js`); use a Claude connector (Atlassian/Slack MCP) only to read, or as a last-resort fallback when the script's env vars are missing.**

Skills that comment on Jira (`clarify`, `bugfix`, `pr`, `plan-deep`) post through
`scripts/jira-comment.py`, because the Atlassian MCP `addCommentToJiraIssue` stores @mentions as plain
text and notifies nobody. The script uses REST API v3 and sends real mention nodes.

```bash
export JIRA_URL=https://yourorg.atlassian.net JIRA_EMAIL=you@org.com JIRA_API_TOKEN=...
printf 'Hi @[Boris](712020:05d5...), which option do you want?\n\n- A: ...\n- B: ...\n' > draft.md
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" post AR-526 --file draft.md   # add --dry-run to see the ADF
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" edit AR-526 <comment-id> --file draft.md   # replace body, no re-notify
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/jira-comment.py" delete AR-526 <comment-id>
```

| Syntax | Result |
|---|---|
| `@[Name](accountId)` | real @mention (`@[](accountId)` looks the name up) |
| `**bold**`, `` `code` `` | bold, inline code |
| `[text](https://url)` | link |
| `- item` / `1. item` | bullet / numbered list |
| `# Heading` | heading |
| `![caption](/abs/path.png)` on its own line, or `--image path[:caption]` | inline image below the text (uploaded as an attachment, caption in italics) |
| `![caption](/abs/path.png)` inside a table cell | the image in that cell (wide table, wide last column); an already-attached same-name file is reused |
| blank line / single newline | new paragraph / line break |

Exit codes: 0 ok · 2 bad usage · 3 env vars missing (skills fall back to MCP; mentions won't notify) ·
4 Jira rejected (incl. failed image upload) · 5 posted but a mention didn't come back. Prints `{"id","url","mentions"}`.
`python3 scripts/jira-comment.py --self-test` runs offline checks.

## Weekend guard

The plugin ships a `PreToolUse` hook (`hooks/hooks.json` → `hooks/weekend-guard.py`) that, on **Saturday and Sunday**, blocks
every tool call that sends something to other people — nothing is sent, and the model is told why:

- sending, editing or scheduling a Slack message (`post-slack.js`, a direct `curl` to the Slack API, the Slack MCP send tools),
- posting, editing or deleting a Jira comment (`jira-comment.py post|edit|delete`, a direct `curl`, `addCommentToJiraIssue`),
- creating, commenting on, updating or merging a pull request (`bitbucket-api.sh POST|PUT|DELETE`, `merge-pr.sh`,
  `gh pr …`, a direct `curl` to Bitbucket, the GitHub MCP create/merge tools).

Reading is never blocked, and neither are drafts or `--self-test` runs; `git push` is covered by the PR-branch guard below. The day is the machine's local day; set
`SHIPKIT_TZ=<IANA zone>` in the environment Claude Code starts in to use another zone. `SHIPKIT_ALLOW_WEEKEND=1` in that
same environment lifts the block for the session (an inline `VAR=1 command` does not). To widen or narrow the guard, edit
the rule lists at the top of `hooks/weekend-guard.py`; `python3 -I hooks/weekend-guard.py --self-test` checks it.

## PR-branch guard (weekend only)

On **Saturday and Sunday** a second `PreToolUse` hook (`hooks/pr-branch-guard.py`) also blocks `git push` to a branch that
**already has an open pull request** — pushing there notifies the PR's people (Slack, e-mail). The model may still
`git commit`; the user pushes. On a weekday it does nothing and does not query any host. It works out the branch from the
command (explicit refspec, `HEAD`, the current branch, or every local branch for `--all` / `--mirror`; `cd` and `git -C` are
followed), then asks the remote's host which branches have an open PR: Bitbucket through `scripts/bitbucket-api.sh`
(`BITBUCKET_USERNAME` / `BITBUCKET_APP_PASSWORD` or `BITBUCKET_API_TOKEN`), GitHub through `gh`. A branch with no open PR is
pushed as usual. When the host cannot be asked (no credentials, network error, unknown host) the weekend push is blocked
as well: unknown is not "no PR". Same clock and switches as the weekend guard above (`SHIPKIT_TZ`,
`SHIPKIT_ALLOW_WEEKEND=1`). Not covered: pushes through an MCP tool, pushes you type in your own terminal, and agents that
do not load this plugin (kiro workers) — so at the weekend `/assign` workers on kiro can still push.

## Stages pane (mod)

`/stages` opens a pane on the newest `.shipkit/pipeline-<ticket>.md` in the session's directory, refreshed every few seconds while it is open
and after every turn. It shows, as `run-pipeline` wrote them: the ticket, the `Flow:` label and a status badge (`⏸ waiting for you`, `● running`
with a spinner while the file is fresh, `✗ failed`, `✓ done`), whose reason is drawn under the stage it concerns (the next one); the stages (`✓` done, `▸` next, `✗` failed); under a stage a
`detail` lines (the branch of each repo under `2 branches`, task counts, verify result, a failure's cause) that opens and closes when the stage is pressed — open by default for the next and
failed stage; `Next:` with an `[ ok ]` button while the run waits for you, which has the same Haiku writer draft the message from the step and the numbers the pane read, then adds the fixed check (verify the step's condition against the real state first; a merge, a push or a Jira post keeps its own go-ahead), puts it in the prompt box and sends it after the same 3 s countdown; it rests five minutes after a press; a summary inside the `clarify` row, shown when it is opened: `OQ: <open> open of <all>` (counted in the spec's `open-question.md`), `✎ draft waiting for you` while `/clarify` holds a drafted question for the user's go-ahead (`pending_comment` in `.shipkit/clarify-<ticket>.md`) and `PO silent for <n> poll windows` (`silent_ticks`) and of blockers, each on the row of the stage it belongs to as `⛔ <n>` — open PR concerns from `pr-<ticket>.md` on `prs`, a `Blocker: [<stage id>: ]…` line the run declared on the stage it names (else the next unfinished one), a failed stage as its ✗ — counts only, the items stay in their files; one link per PR (labelled `root`, or by the submodule's role such as `fe` / `be`, as `run-pipeline` wrote it), the poller's state, and the evidence directory (only the path is the button: it opens the evidence comment — `jira-comment.md`, else `concern-evidence.md` — as a tab in Orca with `orca file open`, or with no comment yet the newest file in the folder, since Orca cannot open a folder; with nothing to open, or when Orca cannot open it, it copies the path); the waits the skills run (a Jira reply from the PO or the reporter, the reviewer's Slack verdict), each with a `[ ping ]` button: a Haiku agent with no tools drafts the reminder from the situation (open count, silent windows, follow-up round, review round), the pane adds its fixed rule (show you the draft before posting), and the result goes into the prompt box and is sent after a 3 s countdown (`[ cancel ]` stops it, and so does editing the box); a box that already holds text only gets the draft added after it and is never sent from. If Haiku fails or takes over 15 s the fixed template is used instead. What is sent only asks the agent to draft: a Jira draft is shown to you before it is posted. The button is offered only when it makes sense: not while a draft already waits for you; for `/clarify` and `/bugfix` only once the PO or the reporter has been quiet for an hour (or has outlasted a poll window — the time is read from when the loop's state file last changed); for the Slack reviewer after one 10-minute window. The message gives how long they have been quiet in real time, and the button rests five minutes after a press; a ⚠️ on a closed row when something inside needs attention (open questions, a draft waiting for you or a silent PO on `clarify`, a branch not yet on origin under `branches`); the arrows ▾ / ▴ open and close a row; and how long ago the file was
touched, with a warning when a run that is not finished has been silent for 30 minutes. It is a Claude Code mod (`hooks/pipeline-pane.tsx`,
named in `hooks/hooks.json` under `modules`), so it needs Claude Code 2.1.287 or later and draws in the terminal, the Desktop app and VS Code
only; older versions and `claude -p` simply do not show it. It reads the state file and never writes it. Test it with `claude plugin test .`.

**The check.** The files only claim a state, so `/stages` also starts a check by a read-only agent (`shipkit:pipeline-collector`, hidden from the model) that runs on the session's own model (`inherit`). It is handed what the files say as claims, verifies them against the real sources (git, the spec directory, Bitbucket, Jira and Slack through their read tools) and answers JSON. The pane draws the files at once, shows `⟳ checking…`, then lays the answer over them: its value wins wherever it gave one (a key it left out was not checked, so the file's value stands), and each place that differs is marked `≠` (a stage row, whose state or detail lines differ, and `Next:`, `PRs:`); the checker is told to answer in fragments, and the pane cuts what is still long (a detail line to 80 characters and 4 per stage, `Next:` to 130). The answer is read defensively (a stage the state file does not list, a link that is not https or a value of the wrong shape is dropped). The agent has `Read`, `Grep`, `Glob`, `Bash` and the Jira/Slack read tools, and `Edit`/`Write` are withheld; that it never writes with `Bash` is its prompt's rule, not a sandbox. One check runs at a time, with a 4-minute limit; the `refresh` chip asks again, and the last answer stays on screen while the next is awaited. It costs the session model's tokens on every `/stages` and every refresh.

## Developing shipkit itself

`git config core.hooksPath .githooks` once per clone; the pre-commit hook runs `bash scripts/self-test.sh` — the pipeline
drift check, the two `plugin.json` versions, the skill-frontmatter lint, every script's self-test and `bash -n`.

## Spec = source of truth in git

Specs are git-tracked files (`specs/NNN-slug/spec.md`), not Jira comments — so they diff, review,
and trace alongside the code. Jira gets a short pointer comment + status transition only.

## What's different from speckit

| | speckit | shipkit |
|---|---|---|
| Commands | 9 (`/speckit.*`) | 1 everyday (`/run-pipeline`) + one skill per stage |
| Files per feature | 5–9 (spec, requirements, plan, contracts, tasks-*, research, …) | **1** (`spec.md`) |
| Per-project setup | copy `.specify/` scripts + templates | `/bootstrap` writes one config file |
| Distribution | per-repo | install the plugin once |
| Vocabulary | issue | **ticket** (Jira) / **PR** (Bitbucket) |
