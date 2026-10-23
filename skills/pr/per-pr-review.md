# /pr — per-PR full review (`--per-pr`, or automatic)

> Loaded by `review-loop.md` Step 1 when `PER_PR` is set or a trigger below fires. The ordinary loop sends one `full review` with every PR link; this mode sends one per PR, so a review is never cut short by the size of the whole ticket.

**When.**
- `--per-pr` → `PER_PR=true` from the start, recorded as `mode: per-pr` in `.shipkit/pr-<ticket>.md`.
- Automatic — checked when the review targets are collected (Step 1) and after every verdict: (a) any review target's diff has more than
  `review.per_pr_file_threshold` files (`skills/pr/config.json`, 100; `git -C <path> diff --name-only origin/<target>...HEAD | wc -l`, the root
  repo the same way), or (b) a verdict's "Not checked" says the bot ran out of tool budget. Either one → `mode: per-pr` from the next trigger,
  and one line to the user that the mode changed and why.

**How.** Targets in Part order (BE before FE), the root last; one review at a time. For each target still `pending`: refresh the Decisions
made blocks (`decisions-block.md`), send `<@<reviewer_id>>` + `slack.review_ask` with **that one PR's link**, wait for its verdict
(Step 3.1, its own `after_ts`), triage and fix it (Step 3.4 to 3.7, `/assign --only` that PR's submodule), then move to the next target.
- **Approvals:** a verdict approves only the PR it was asked about — `## PR approvals` is already per target, so it records `lgtm@<sha>` for
  that PR alone and the others stay `pending`.
- **Rounds:** `round` is counted per PR (`round=<n>` on that PR's line of `## PR approvals`), and `loop.max_rounds` is the cap for each PR. The
  severity stop (4b) applies per PR.
- **Reporting:** at decision points only, as in the ordinary loop (a verdict that needs the user, every PR signed off, a cap).
