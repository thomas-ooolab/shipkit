---
type: llm
---

PASS if the answer reopens OQ-4 as `- [ ]` (the PO's answer takes precedence over the mockup), keeps the old decided text after a `previously:` marker, and names the reopened item in the Jira comment as the line it replaced.
FAIL if the mockup tick stands, or the old text is dropped.
