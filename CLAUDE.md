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
- Secrets never go on a command line: pass them to curl on stdin (`curl -K -`), as `merge-pr.sh` and `bitbucket-api.sh` do.
