---
type: llm
---

PASS if F-02 (comment only) is fixed in the same `/assign` round with no new full review, while F-01 (changes behaviour, no page size decided) and F-03 (unclear what is right, the spec is silent) go to the follow-up list and are not implemented by this loop.
FAIL if F-01 or F-03 is implemented, or if F-02 is left as a follow-up, or if a new full review is sent.
