---
type: llm
---

PASS if the answer fixes F-02 and F-03 itself in the same `/assign` round, before signing off (not deferring them): the comment and doc fixes in the submodule, and the root `docs/features/reports.md` in the root repo so the root PR carries it; it sends no new `full review`, marks the PRs `lgtm@<approved sha> (+ nit fixes <new sha>, no re-review by design)`, and the follow-up list does not contain F-02 or F-03 (it is empty / none). Fixing them despite being outside the allowlist is correct (no behaviour change).
FAIL if F-02 or F-03 goes to the follow-up list instead of being fixed, if it asks for a new full review because of them, or if it treats the out-of-allowlist doc as a needs-decision blocker.
