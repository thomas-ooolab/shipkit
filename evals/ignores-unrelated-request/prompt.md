---
description: "A small coding request no shipkit skill is for; none may be invoked."
tags: [routing]
max_turns: 8
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
---

In this snippet rename the variable `tmp` to `count` and show me the result:

    tmp = 0
    for item in items:
        tmp += item.qty
    print(tmp)
