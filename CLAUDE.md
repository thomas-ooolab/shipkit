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

`evals/` is the plugin's eval suite (Claude Code docs: *Test plugins with evals*). Each case is a plain request a user would type and a
grader on the steps Claude took. Today: one `routes-*` case for each of the 17 skills checks that Claude picks it on natural phrasing
(`tool_used: Skill`, free, no judge call) and `ignores-unrelated-request` checks no shipkit skill fires on a small coding task.

- Run from the plugin root: `claude plugin eval . --trust-plugin --ablation none -j 4 --no-publish` (18 cases × 3 runs ≈ $6); add
  `--runs 1` while iterating (≈ $2). Without `--ablation none` every case also runs with no plugin: `Δ` on a `tool_used: Skill` case is
  trivially +1 (the skill cannot be called without the plugin), so read the `WITH` column.
- Every run and judge grader is a model call: it is **not** in `scripts/self-test.sh` or the pre-commit hook. Run it after changing a
  skill's `description` (the thing routing depends on) or adding a skill, and add a `routes-<name>` case for a new skill.
- A case that fails on `tool_used: Skill` means the skill's `description` does not trigger on that phrasing: fix the description, not
  the case. Results go to `evals/results/` (gitignored).
