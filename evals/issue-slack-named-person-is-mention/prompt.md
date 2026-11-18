---
description: "2026-11-18: a person merely NAMED in a Slack draft (a QC engineer the user names by Jira handle) is written as a real <@U…> mention with the Slack id, never as the plain handle or a Jira accountId."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are /developer. The user wrote: "nhắn Thang là fix AR-674 xong trên staging, báo chi.ttk retest #10". You already read the DM history with Thang (Vietnamese, the user calls him "anh Thắng" and says "em"). Earlier in this session you read a Slack thread where Kim Chi, the QC engineer, wrote a message whose `user` field was `U0510JSBPV5`; in Jira the same person is handle `chi.ttk`, accountId `5b10a2844c20165700ede21g`. Write the exact DM text you show the user for approval, then say how you wrote the QC engineer.

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
