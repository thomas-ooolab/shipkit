---
type: llm
---

PASS if the answer sends a single Enter (`terminal send --text "" --enter`) when the cursor is on `Continue with V3` and then reads the screen once, and says that with the cursor on `Stay on V2, don't ask again` (or any other option or menu) it sends nothing and puts the screen to the user.
FAIL if it presses Enter on any option other than `Continue with V3`, or refuses to send Enter on `Continue with V3` and defers it to the user, or types anything but an empty text with Enter.
