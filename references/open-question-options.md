# Options in an open question — shared by `/spec-from-ticket` and `/plan-deep`

An open question goes to the PO, who answers the options as written. The options must be real, and the dev's own ideas must not pass
as facts.

1. **An option that presupposes something the system can do — retry, redo, re-score, undo, notify, resend, schedule, roll back — is
   written only after you looked for that ability in the code.** Found → cite it (`file:line`). Not found → the option says "does not
   exist today, would need building", or it is dropped. Never write "…and it is retried automatically" because it reads naturally:
   search the failure path first (a comment such as "nothing re-drives it" is a finding).
2. **Options come from a source** (the ticket, the spec, a Jira reply, the code). An option only the dev thought of is a **proposal**
   and is labelled as one.
3. **An option or fallback that leans on a capability of another ticket — "X from `<OTHER-KEY>`", whether it exists, is planned or
   will land — is a *borrowed capability*.** It carries a verification line: where X is built (that ticket's spec REQ, its branch
   `file:line`, a route in the API contract) or the words `not found`. A PO's "rely on X from `<OTHER-KEY>`" is not a verification, it
   only shows the PO said it. `not found` → before the item is written, tell the dev in the terminal (`⚠ borrowed capability not found: X of <KEY> — searched <where>`);
   X is the recovery path of no option, and the option says plainly "no ticket builds X yet" (or is dropped).
4. **Keep the checked facts apart from the proposals**, as dev-only sub-lines under the item (`/clarify` never copies them into the
   Jira comment; it rewrites the options in business language):
   ```markdown
   - [ ] **OQ-N** — {question, plain business language} — blocks: REQ-NNN
     - checked (dev-only): {what the code does today} (`file:line`); {ability an option relies on}: exists (`file:line`) | not found (searched: <terms>)
     - values (dev-only): {classification}: {value} → {side of the split}, {value} → {side} (`file:line`) | one value only
     - borrowed (dev-only): {X} of <OTHER-KEY>: built in <spec REQ | branch file:line | api route> | not found (searched: <terms>)
     - proposed (dev, unconfirmed): A. {option}  B. {option — needs building: <what>}
   ```

5. **A question whose options split on a classification — a type, kind, status, role or plan; "which type counts as X", "only if
   there is at least one Y", "N Xs and M Ys" — is written only after you listed the real values in the code** (enum, constants,
   distinct values in the table), in the same turn, and the `values:` sub-line is required. Put each value on a side of the split by
   what the code and the product do with it, never by whether its name matches the ticket's word (`scripted` and `dynamic` may both
   be what the ticket calls "roleplay"). Name the values in the question too. Every value on one side, or only one value → the split
   is empty: drop the question, state the consequence in the spec ("every task is a roleplay, so the condition always holds"; "the
   two counts are always equal"), and strike the item `dropped: <fact> (file:line)`. No `values:` line, no item.
6. **`[not specified — ask before implementing]`, "values not enumerated yet", "settled at plan time" stand for a lookup, not a
   deferral.** When the missing fact is one the code holds (the values of a field, what a screen does today), grep or read first and
   ask only if the code cannot answer; `checked:` then lists what was searched. A choice only the PO can make stays a PO question.
7. **A line recorded as decided or resolved (a spec Key decision, an answered item, a dev note) is re-read whenever a new fact
   arrives** — a code finding, a PO reply, another ticket. A fact that contradicts it or empties it reopens the item, and the new
   line says which one it replaced.

Bad: "OQ: which task type counts as a roleplay? (`checked:` values not enumerated yet, settled at plan time)" — the code has two
task types and both are AI roleplay, so the condition "at least 1 roleplay task" is always true and the PO is asked about nothing.
Good: `values: task type: scripted → roleplay, dynamic → roleplay (coursebuilder.go:101-105)` → no question; the spec says the
condition always holds, and "N modules and R roleplays" shows the same number twice.

Bad: "B: the call is not shown as scored until the record is saved, and the save is retried automatically." (the worker's code says
nothing re-drives a failed save, so B offers the PO something that cannot happen.)
Good: `checked: a failed save is not retried (<worker file>:<line>, "no retry")` · `proposed: A. keep as today, the call shows as scored even if the record failed; B. hold the call until the record is saved — needs building: a retry.`
