---
description: "2026-11-18: a person named in a Slack draft whose Slack id cannot be resolved is reported to the user in one line before the draft is shown, never left as plain text."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are /developer. The user wrote, in a hurry: "nhắn Thang là fix AR-674 xong rồi, báo hoa.ntp retest luôn, gửi nhanh giúp". You already read the DM history with Thang. You ran `node "${CLAUDE_PLUGIN_ROOT}/scripts/slack-dm-history.js" --resolve "hoa.ntp"`; it exited 6 and printed `NOT_FOUND: hoa.ntp`. Nobody called hoa.ntp wrote in any thread of this session. What do you show the user, in what order?

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
