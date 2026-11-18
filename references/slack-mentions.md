# A person named in a Slack post is a mention — shared by every skill that posts to Slack in the user's name

Applies to every Slack draft or post made in the user's name: a thread reply, a DM, a seed ping, a sign-off ack.

1. **Every person the text names is written `<@U…>`** — the person being answered, and also a QC engineer, a PM, a teammate, a person
   known only by a Jira handle (`chi.ttk`) or a display name. Typed as plain text (`chi.ttk`, `@chi`, "Kim Chi") nobody is tagged.
2. **Get the id before the draft is shown.** A person you already met in this session as the `user` of a Slack message
   (`conversations.replies` / `history`) keeps that id. Otherwise resolve them:
   `node "${CLAUDE_PLUGIN_ROOT}/scripts/slack-dm-history.js" --resolve "<name | Jira handle | email | U… id>"` prints `USER <U…> <name>`.
   The Slack id and the Jira `accountId` are different ids: never reuse a Jira `accountId`, never type an id from memory.
3. **Not resolved** (exit 6 not found · 7 ambiguous · 8 scope missing · 3/4 no token or Slack refused) → one line to the user **before the draft is
   shown** (`chi.ttk: no Slack user found — who is it?`) and ask; the word is never left in the draft as plain text and the person is never dropped quietly.
4. **Backstop:** `post-slack.js` refuses a text that still holds a bare `@name` or a handle-shaped word (lowercase dotted, `chi.ttk`) outside `<@U…>`,
   a link, a URL and backticks — exit 6, `MENTION_ERROR` naming the word, nothing posted. A handle that is meant literally goes in backticks.
5. A Jira comment mentions people differently (`@[Name](accountId)`, `jira-comment.py`); this file is Slack only.
