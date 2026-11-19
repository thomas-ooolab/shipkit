---
description: "AR-684: the PR-slot timer exited 2 'line not found at start' because the call was composed with a leading space; a malformed call is re-armed once after reading the state file, with the script reading the value itself, and only a repeated failure becomes the ask-the-user fallback."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/run-pipeline AR-684 --bug auto`. The root answered the PR slot question with `start at 2026-11-19T15:11:00+07:00`. You wrote `Status: waiting-user · pr slot 15:11` and `  - detail: pr slot @ 2026-11-19T15:11:00+07:00` in `.shipkit/pipeline-AR-684.md` and started the slot timer as `python3 -I notify-desktop.py --wait-only --after 2400 --unless-changed .shipkit/pipeline-AR-684.md "Status:" " waiting-user · pr slot 15:11"`. It ended at once with exit 2 and stderr `line not found at start: .shipkit/pipeline-AR-684.md 'Status:' ' waiting-user · pr slot 15:11'`. The state file still has the `Status:` line exactly as you wrote it. What do you do now, in order? What goes in the `Status:` text, and do you ask the user "start /pr now?"

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
