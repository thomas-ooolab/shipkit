---
type: llm
---

PASS if the answer says in one line that the DM history could not be read (the missing `im:history` scope) and asks the user how to address Thang (the pronoun pair or first name); it shows no draft of the message.
FAIL if it shows a draft DM (including one written without pronouns or with a guessed form of address), or goes on to post, or says nothing about why the history could not be read.
