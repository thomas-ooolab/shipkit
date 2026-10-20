# Humanize free-form posts — shared by every skill that speaks as the user on Jira or Slack

Applies to prose posted in the user's name: a Jira comment, a Slack thread reply, a DM, a seed ping. It does not apply to fixed
templates (`/verify`'s evidence table, `/plan-deep`'s one-line note), code, or tables.

1. **Draft** the text under the skill's own rules (language, business wording, tags).
2. **Load `humanizer:humanizer`** (Skill tool) and apply it to the draft yourself: it is a pattern guide, so it returns no
   rewritten text. Edit the draft by its patterns; its pattern list and notes stay in the terminal.
3. **Check the rewrite before using it.** It must keep, character for character: `@[Name](accountId)` and `<@U…>` mentions, URLs,
   ticket keys, `OQ-N` / `REQ-NNN` codes, each `N. ` list line with its number, `(n/n)` part markers, and attachment references
   ("see the image below"). It must keep the draft's language, add or drop no fact, number or name, and still obey the skill's
   own rules (no field or endpoint names in a Jira comment, no bolded outline). Any miss → fix that spot by hand, or keep the
   draft's wording there.
4. **Show and post the checked rewrite.** Where the skill waits for approval, the approved text is this version, and the text
   posted is exactly the text approved.

Humanizer not installed (the Skill call errors) → one terminal line, "humanizer plugin not installed, posting unedited", and
carry on with the draft. Never block a post on it.
