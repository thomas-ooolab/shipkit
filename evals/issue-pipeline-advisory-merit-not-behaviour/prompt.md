---
description: "AR-686 (SPEC=none bug ticket): advisories sorted by whether the fix needs a decision, data work or a policy, not by whether it changes behaviour; a same-class sink the PR leaves out is the user's decision; every real item left gets a draft follow-up."
tags: [issues]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

You are running `/run-pipeline AR-686 --bug auto` (`SPEC=none`). The ticket's first sentence: "Customer text must not reach HubSpot or Slack with unescaped quotes." The PR fixes the quote rule for the count and the push to HubSpot. Stage 3 review reported `0 blocking, 8 advisory`:
1. a security regression test contains an assertion that cannot fail (it compares the result with itself);
2. a test name has no Scenario part;
3. the deal-signals row uses a looser quote rule than the count and the push (a file the branch diff does not change);
4. values already written to customers' CRM records still hold the unescaped quotes (needs a one-off clean-up);
5. a Slack section can exceed the 3000-character limit (a bug that was there before this branch);
6. the HubSpot call-body field (`hs_call_body`) has the same quote problem and this PR does not touch it;
7. Slack has no escape for `*`, `_` and `~`;
8. the count reflects the last push, not the total.
Which ones go to the fixer, which become what, and what does the run do about each of the others? `Rounds:` is `1/6`.

Answer from shipkit's own rules only (read the skill and the files it points to); do not run anything.
