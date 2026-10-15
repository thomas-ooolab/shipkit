# shipkit — working on this plugin

## Changing the pipeline order or adding/removing a stage

The feature flow's order is restated in several places, and they drift. When you change it:

1. Edit `skills/run-pipeline/stages.txt` (the canonical order).
2. Update every place that restates it — `skills/run-pipeline/SKILL.md` (stage list + stage bodies),
   `skills/help/SKILL.md`, `skills/developer/SKILL.md`, `README.md` (pipeline diagram), the `Next:` lines of
   `spec-from-ticket` / `plan-deep`, and `verify`'s "How it fits the pipeline". The list lives in
   `scripts/check-pipeline.py` (`CHECKS`); add a row there when a new file starts restating the flow.
3. Run `python3 -I scripts/check-pipeline.py` — it must exit 0. It checks skill names and their order only,
   so also grep for sentences that describe what a stage *does* (e.g. who posts the evidence to Jira).
   A `pre-commit` hook runs it for you: enable it once per clone with `git config core.hooksPath .githooks`.
4. Bump the version in `plugin.json` and `.claude-plugin/plugin.json`.

Each skill also gates on `SHIPKIT_CONFIG_EXISTS` (inject `probe.sh resolve`, stop with "Run `/bootstrap` first");
a new skill that reads `.shipkit/config.yml` needs the same gate.
