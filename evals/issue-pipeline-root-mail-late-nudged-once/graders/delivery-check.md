---
type: llm
---

PASS if the answer: records the message id on the detail line right after the send (`asked the root @ <time>: <short> msg msg_19f3d6d966ba delivered not yet` or equivalent); about 150 seconds after the send (2-3 minutes) runs the delivery check (`scripts/root-delivery.py --run run_11d0f461afbc --msg msg_19f3d6d966ba --terminal <root_terminal>`, or equivalently reads `delivered_at` through `orca orchestration inbox --terminal run:<run> --full --json`); with `delivered_at` empty and the root idle at an empty input box, types Orca's own wake line `You have 1 orchestration message. Run orca orchestration check --run <run>.` with Enter into the root terminal and rewrites the detail line to say it was nudged (once per message, never a second nudge); with text in the box or the root mid-turn, types nothing and checks again after 2-3 minutes; and keeps waiting for the answer after the nudge (it does not ask the user yet).
FAIL if it just waits for the answer (or the 2 hours) without checking delivery, types anything when the box holds text or the root is mid-turn, nudges a second time, asks the user "start /pr now?" at 08:45, or treats the nudge as the answer.
