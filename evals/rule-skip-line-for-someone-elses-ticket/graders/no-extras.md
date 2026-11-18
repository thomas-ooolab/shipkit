---
type: llm
---

The skill prints ONE short sentence in the terminal. PASS if the line the answer says it prints is a single sentence of the form "Skipped: AR-9 is Alice's ticket." with nothing else printed: no account IDs, no commit emails, no list of what was checked, no remark that the QC post is not for the user.
FAIL if the printed output is more than that one sentence. Explaining in the answer why nothing else is printed does not count as printing it.
