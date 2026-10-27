# Restriction claims — a requirement that narrows who may see or do something on an entity

Applies to a claim of kind (a) whose scope is narrower than what the code allows today: "only the `<entity>` they own", "assigned
to their team", "their own", "shared with them". Runs inside Step 3c, before any design, option or PO question is written.

1. **Access matrix first.** Rows: every role the code knows. Columns: every route that reads or acts on the entity — list, detail,
   create, update, delete, assign / enroll, and the new action. Find the routes from the route registrations and handler folders, not
   from the screens the ticket names. Each cell is the gate that route applies to that role today with `file:line`, or `no gate`, or
   `not found (searched: <terms>)`. Write it as `## Access matrix` in `cross-check.md`. A guard that exists for another purpose
   (analytics scoping, a different entity) is not a cell: say so in the row note.
2. **Noun check.** Each noun that defines the scope — own / owner, team, assigned, shared with — must exist as a stored relation
   (column, join table, membership) **and** be applied by at least one route. One line per noun in `## Dev notes`:
   `<noun>: stored at <file:line>, applied at <file:line>` | `stored, never applied (<file:line>)` | `not found (searched: <terms>)`.
   Not stored, or never applied → `[spec-vs-code] premise-risk: "<noun>" is not a relation the system keeps`. Around a premise-risk noun
   no column, backfill, scope, task or PO question that defines the noun is designed: a concept the system lacks is a dev decision
   with its evidence, told to the PO to object to, never asked as "what does own mean?".
3. **Coherence.** The new rule is the only gate on the entity when every other cell of the same role in the matrix is `no gate` or
   a workspace-only check. Then label the item `[incoherent-restriction]` and ask the PO the **purpose**: "what is this limit meant to
   prevent?", in business words, saying plainly what that role can already do today (taken from the matrix row). Both sides are
   quoted: the rule, and the matrix row with its `file:line`. The question offers no definition of own / team.
4. **Signal to return here.** While designing or planning, if making one rule work needs a new column, a backfill, extra tasks or extra
   questions that exist only to give that rule meaning, stop and redo 1–3. Say it in `## Dev notes`: `complexity added only to make
   REQ-NNN run: <what>`.

5. **Two exits, never a silent third.** A `premise-risk` or `[incoherent-restriction]` leaves this skill one of two ways.
   (a) **Ask the PO the purpose** — "what is this limit meant to prevent?" — never the definition of a concept the system has no
   relation for. (b) **Dev decision with evidence:** state the proposed decision and its evidence (`file:line`, the matrix row) in the
   terminal and ask the user to confirm it. Only after the confirm, record it under the item as
   `decided (dev, confirmed <date>): … — evidence: …`; `/clarify` then tells the PO in business words, as "decided — object if you want
   it otherwise". No confirm → the item stays open and nothing is designed on it. A decision that reverses an earlier one (a spec Key
   decision, an answered item, a PO reply) says which one and what changed; one that reverses nothing adds nothing. A confirmed `decided` item does not block the REQ it serves; it stays `[ ]` until the PO
   answers or the user closes it, and a PO objection reopens that REQ (`open-question-options.md`, rule 7).

```markdown
## Access matrix — <entity>
| route | <role-1> | <role-2> | <role-3> |
|---|---|---|---|
| list | <gate file:line \| no gate> | … | … |
| delete | no gate (<file:line>) | … | … |
```

An `[incoherent-restriction]` item in `open-question.md` follows the `[ticket-conflict]` shape: question first, then the rule as an
indented quote with its source and the matrix row as an indented `code:` line.
