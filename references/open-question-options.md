# Options in an open question — shared by `/spec-from-ticket` and `/plan-deep`

An open question goes to the PO, who answers the options as written. The options must be real, and the dev's own ideas must not pass
as facts.

1. **An option that presupposes something the system can do — retry, redo, re-score, undo, notify, resend, schedule, roll back — is
   written only after you looked for that ability in the code.** Found → cite it (`file:line`). Not found → the option says "does not
   exist today, would need building", or it is dropped. Never write "…and it is retried automatically" because it reads naturally:
   search the failure path first (a comment such as "nothing re-drives it" is a finding).
2. **Options come from a source** (the ticket, the spec, a Jira reply, the code). An option only the dev thought of is a **proposal**
   and is labelled as one.
3. **Keep the checked facts apart from the proposals**, as two dev-only sub-lines under the item (`/clarify` never copies them into the
   Jira comment; it rewrites the options in business language):
   ```markdown
   - [ ] **OQ-N** — {question, plain business language} — blocks: REQ-NNN
     - checked (dev-only): {what the code does today} (`file:line`); {ability an option relies on}: exists (`file:line`) | not found (searched: <terms>)
     - proposed (dev, unconfirmed): A. {option}  B. {option — needs building: <what>}
   ```

Bad: "B: the call is not shown as scored until the record is saved, and the save is retried automatically." (the worker's code says
nothing re-drives a failed save, so B offers the PO something that cannot happen.)
Good: `checked: a failed save is not retried (<worker file>:<line>, "no retry")` · `proposed: A. keep as today, the call shows as scored even if the record failed; B. hold the call until the record is saved — needs building: a retry.`
