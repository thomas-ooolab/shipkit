# /verify — the evidence table (Step 6)

> Loaded by SKILL.md after the gate is `PASS`, and again when the user asks for the Jira comment ("soạn jira",
> "draft the Jira comment") while the evidence of a `PASS` is on disk. Nothing goes to Jira here.

## The file — one name for every kind

`.shipkit/evidence/<TICKET>/jira-comment-<YYYYMMDD-HHMM>.md` (`date +%Y%m%d-%H%M`, the time it is written). The PNGs and
data files it embeds are already beside it.

- **Written** at the end of a `PASS` run, and on request: the user asks for the Jira comment → write it from the evidence
  already on disk, with the template below. No re-run, no table composed by hand, no file anywhere else (not the scratchpad,
  not the repo root).
- **One file at a time.** After writing it, delete every older draft of the ticket: each `jira-comment-*.md` and the names an
  earlier version used, `jira-comment.md` and `concern-evidence.md`. `FAILED` / `INCOMPLETE` write nothing and delete them all,
  so `/merge` never sends proof of code that has since changed.
- Which template: the checks came from the spec (no `--concern`) → **Feature**; `--concern` (how `/bugfix` calls it) → **Bugfix**.
  `--no-jira` writes no file.

## The proof cell — one rule for both

- **FE check →** the screenshot itself: `![<caption naming the check>](/abs/path/<file>.png)`, several per cell separated by a
  space. Open every PNG first and confirm it shows what the row claims. `jira-comment.py` uploads it (reusing one already
  attached) and embeds it in the cell, so no `--image`. **Never** a file name, a path in backticks or a 📎 as the proof of an FE
  check: the reader sees the picture, not where it lives.
- **BE check →** never a token, credential, real personal data or a raw database dump; the full file stays in
  `.shipkit/evidence/`. **Feature:** a redacted excerpt (method + path, status, the key fields that show the requirement holds).
  **Bugfix:** the observed result in business words ("a Manager is refused another team's rep and sees their own team's"), with
  **no endpoint, path or table name**: the reader is the tester, not a developer.
- A pipe inside a cell is written `\|`. Headers and cells are in the language of the ticket's comments.

## Feature — a single table, nothing else

The first header cell is the literal `/verify`: it is the marker that finds this comment later (send mode). One row per
requirement and per named variant; a `UI` row only when Part A ran. No intro, no prose, no "not checked" row.

```
| /verify | Requirement | FE/BE | Check | Result | Evidence |
|---|---|---|---|---|---|
| REQ-001 | <the requirement in business words> | FE | <what was done> | ✅ PASS | ![REQ-001 step 1](/abs/path/REQ-001-after.png) |
| REQ-002 | <…> | BE | <what was done> | ✅ PASS | `GET /…/digest/weekly` → 200, `calls_total` = 1 |
| UI | Matches design-contract.md | FE | desktop / tablet / mobile | ✅ PASS | ![1280](/abs/path/ui-1280.png) ![768](/abs/path/ui-768.png) |
```

## Bugfix — the table `/bugfix` pastes into its own comment

One row per concern and per named variant, in the tester's numbering. The file holds this table and nothing else: the prose
around it (the @-mentions, a decision still open) is `/bugfix`'s own comment, and it pastes these rows as they are, never
retyped or reworded.

```
| Concern | FE/BE | Check | Result | Evidence |
|---|---|---|---|---|
| 3. SkillQuotient over time | FE | Gave the chart the tester's exact values | ✅ PASS: a dot only where there is a value, all six labels visible | ![3 chart after the fix](/abs/path/3-sq-chart-after.png) |
| 5. Total calls vs call log | FE | Period 6M | ✅ PASS: total 26 and "26 of 26 calls shown" | ![5 totals match the log](/abs/path/5-totals-vs-log-after.png) |
| 1. Other reps' data readable | BE | Called the API as a Manager for a rep outside the team | ✅ PASS: refused with 403; own team 200 | a Manager opens own-team reps and is refused the others |
```

A concern that is `FAIL` or `UNVERIFIED` has no row: the gate is not `PASS`, so no file is written.

## A picture that does not show its row

The table carries the run's results as they are: never reword a Requirement, Check or Result cell to fit a picture. If a PNG
does not show what its row claims, **write no file**: name the row and what the picture shows instead, and leave the call (re-capture
the screenshot, or re-run the check) to the person. Silently weakening a claim hides the gap from the reader.

## After writing

Report `verify: evidence for <TICKET> ready — <path>` (Feature: add "it will be sent by /merge just before the status change").
Stop there: sending is Step 7.
