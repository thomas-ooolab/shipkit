# shipkit — working on this plugin

## Changing the pipeline order or adding/removing a stage

The feature flow's order is restated in several places, and they drift. When you change it:

1. Edit `skills/run-pipeline/stages.txt` (the canonical order).
2. Update every place that restates it — `skills/run-pipeline/SKILL.md` (stage list + stage bodies),
   `skills/help/SKILL.md`, `skills/developer/work-mode.md`, `README.md` (pipeline diagram), the `Next:` lines of
   `spec-from-ticket` / `plan-deep`, and `verify`'s "How it fits the pipeline". The list lives in
   `scripts/check-pipeline.py` (`CHECKS`); add a row there when a new file starts restating the flow.
3. Run `bash scripts/self-test.sh` — it must exit 0 (it runs `scripts/check-pipeline.py` among other checks). The drift
   check looks at skill names and their order only, so also grep for sentences that describe what a stage *does* (e.g. who
   posts the evidence to Jira, what `/pr` says comes next). A `pre-commit` hook runs it for you: enable it once per clone
   with `git config core.hooksPath .githooks`.
4. Bump the version in `plugin.json` and `.claude-plugin/plugin.json`.

Each skill also gates on `SHIPKIT_CONFIG_EXISTS` (inject `probe.sh resolve`, stop with "Run `/bootstrap` first");
a new skill that reads `.shipkit/config.yml` needs the same gate.

## Writing or editing a skill

- Frontmatter: `description` starts with "Use when" and names triggering conditions only — never the workflow; at most 1024
  characters; `argument-hint` whenever the Trigger line shows arguments. `scripts/check-skills.py` enforces it.
- Keep SKILL.md to what every run needs. A long, conditional section (one mode, one flag, one phase) goes in a file next to
  it (`skills/<name>/<topic>.md`) and the SKILL.md says "REQUIRED: Read `${CLAUDE_PLUGIN_ROOT}/skills/<name>/<topic>.md`
  and follow it". Text two skills share goes in `references/`.
- Nothing project-, person- or language-specific in a skill, agent or template: a channel or bot id lives in
  `skills/pr/config.json`, a language / timezone / hours / SSH rewrite in `.shipkit/config.yml`, a stack convention in the
  target project's own `CLAUDE.md`. Examples use placeholders (`service-be`, `<submodule>`).
- Never write a dollar sign followed by a digit in a SKILL.md command (awk's third-field print, positional shell args): the skill loader
  substitutes them with the command's arguments. Use `git rev-parse HEAD:<path>`, `sed` with a backslash-digit group, or a
  script file.
- Before a skill writes a new script or a long one-off command, look in `references/existing-scripts.md`, `scripts/` and the other
  skills' folders: reuse a script that does it, extend one that nearly does (a mode or flag, same exit codes and error text, a
  `--self-test` case), and write a new one only when none fits — then add its row to `references/existing-scripts.md`.
- A skill that answers a person or reports a result points to `references/answer-with-evidence.md` (every claim has evidence fetched
  in that turn; a fact a read-only check can settle is checked before the answer, "not verified" only for what cannot be checked, with
  what blocks it, who opens it and what was tried) instead of restating it, and never words an answer "not checked" for something it could have read.
- Secrets never go on a command line: pass them to curl on stdin (`curl -K -`), as `merge-pr.sh` and `bitbucket-api.sh` do.

## Evals (`claude plugin eval`)

`evals/` is the plugin's eval suite (Claude Code docs: *Test plugins with evals*). Three kinds of case, by tag:

- `routing` — 17 `routes-<skill>` cases (one per skill) and `ignores-unrelated-request`: a plain request, and a `tool_used: Skill`
  grader says Claude picked the right skill. Free graders, no judge call.
- `rules` — 14 `rule-*` cases from the standing feedback in the auto-memory (Jira writes through the script, merge hand-off order,
  Slack DM history first, questions in the user's language) and from recent fixes (AR-676, AR-677, AR-678).
- `issues` — 58 `issue-*` cases from the decisions and bug fixes recorded in claude-mem (`/bugfix` held / reopened / fix-round cap,
  run-pipeline stop and slot rules, root coordinator, `/developer` go-signal, `/pr` review loop, `/verify`, `/clarify`). Each is a
  scenario with its facts in the prompt and a rubric (`llm` grader) or a regex on the answer.

Run it with `bash scripts/run-evals.sh [--tag routing|rules|issues] [--case <glob>] [--runs <n>]` — it adds what the `rules` and `issues`
cases need: `--scaffold` (each builds a small fixture repo with a `.shipkit/config.yml` from its own `scaffold.sh`, because every skill
gates on that file) and one Bash grant for `probe.sh`. Every run and every judge vote is a model call, so it is **not** in
`scripts/self-test.sh` or the pre-commit hook: all 90 cases at the default 3 runs cost tens of dollars; `--runs 1` on one tag costs ≈ $10.

- **A change that alters what an agent decides comes with its eval case in the same commit** — skill or reference text, a rule, a hook, a
  script a skill relies on: add a case (or update the one that pins the old rule), run it with `bash scripts/run-evals.sh --case <name>`
  (≈ $1), and put the result in the commit message next to the self-test. A bug an eval or a user report turns up gets its `issue-*`
  case first, shown failing on the old text, then passing. Not needed for a typo, a version bump or text that changes no behavior.
- Run it after changing a skill's `description` (routing depends on it) or a rule a case pins, and when you add a skill (add a
  `routes-<name>` case). When a memory entry or a bug report names a rule the agent got wrong, add an `issue-*` case with the facts
  in the prompt and a rubric of concrete PASS and FAIL conditions.
- A failing `routes-*` case means the skill's `description` does not trigger on that phrasing: fix the description, not the case. A
  failing rule or issue case is either the skill text (unclear or changed) or the rubric (check the judged excerpt in the report
  before touching either); keep rubrics to what the skill says, a judge fails an answer for a detail the skill never asked for.
- Without `--ablation none` each case also runs with no plugin. A `tool_used: Skill` grader cannot pass without the plugin, so `Δ`
  there is trivially +1: read `WITH`. On the 43 rule and issue cases (1 run each) `Δ` was +1.00 on 36; these answer the same without
  the plugin, so they are regression guards, not proof the plugin adds anything: `issue-bugfix-spec-edit-needs-decision`,
  `issue-clarify-claims-need-a-source`, `issue-developer-mention-is-not-a-go`, `issue-pr-no-retrigger-without-commit`,
  `issue-verify-contradicting-picture-blocks`, `rule-dirty-worktree-not-removed`, `rule-question-in-users-language` (the language line
  is in the prompt, it checks the skills obey it).
- A run is a temporary home with no memory, no Jira, no Slack: it checks what the agent decides from the skill text, not what a
  script or a live system does. Results go to `evals/results/` (gitignored).
