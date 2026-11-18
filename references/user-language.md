# The language spoken to the user

Everything said **to the user** is in the user's language: terminal lines, questions (`AskUserQuestion` and its options), reports,
the daily briefing, a draft shown for approval. Not in it: a Slack reply (that is the thread starter's language, `developer/SKILL.md`),
text posted to Jira (the ticket's comments' language), code, commits, skill files, and whatever the memory entry itself says stays in
another language.

1. **Resolve it once per session** with `python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/user-language.py`. It reads `language:` of
   `.shipkit/config.yml` first (the user set it on purpose), then the auto-memory of earlier sessions — this project's, then the
   user's other projects' — and prints `language: <code>`, the file it came from and the words that named it. The plugin's
   SessionStart hook runs the same script and puts the answer in the session's first context, so a session that was told the
   language does not run it again.
2. **`language: unknown`** → the language of the user's own latest message; none → English. The user is never asked which language.
3. **The resolved language beats the language of the message.** A task pasted in English to a user whose memory says Vietnamese is
   still answered in Vietnamese. What the user says in this session ("answer in English") beats memory, for the rest of the session.
4. **Hand it down.** Every agent or worker this session starts gets `language: <code>` in its prompt or request. One that was given
   none runs the script itself before it writes a line to the user.
