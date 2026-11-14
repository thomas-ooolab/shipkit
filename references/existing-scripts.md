# Scripts that already exist — look here before writing one

Before a skill, or a session running a skill, writes a new script or a long one-off command (a poll loop, a Slack or Jira call, a
Bitbucket request, a wait), check this list and `scripts/` and the skill folders. Order:

1. A script here already does it → run it as it is.
2. One does most of it → extend it (a new mode or flag, the same exit codes and error text, a `--self-test` case) in the plugin, then run it.
   Do not copy it into the scratchpad and edit the copy: the next session would write the same copy again.
3. Nothing fits → write the new script in `scripts/`, with a `--self-test`, add its row below, and say why none of the above fit.

The checks stay in the plugin and the token stays off the command line (stdin to curl, as the scripts here do).

| Need | Script |
|---|---|
| Send, edit or delete a Slack message, with files | `node scripts/post-slack.js` |
| Wait for a reply in a Slack **thread** (poll) | `bash scripts/wait-for-slack-reply.sh --until others` |
| Wait for the answer to a **DM** you sent (top-level message of the `D…`/`G…` channel) | `bash scripts/wait-for-slack-reply.sh --until dm` |
| Wait for the review bot's verdict in `/pr`'s thread | `bash scripts/wait-for-slack-reply.sh --until verdict` |
| Same as the thread wait, pushed by Socket Mode (`SLACK_APP_TOKEN`) | `node scripts/wait-for-slack-event.js` |
| Watch every Slack notification (Observer, `/developer` without a URL) | `node skills/developer/observe-slack.js` |
| Post, edit or delete a Jira comment | `python3 scripts/jira-comment.py` |
| Wait for a new Jira comment | `bash scripts/wait-for-jira-comment.sh` |
| One Bitbucket REST call | `bash scripts/bitbucket-api.sh` |
| Merge a PR, read pipelines, wait for them | `skills/merge/merge-pr.sh`, `pipelines-status.py`, `wait-pipelines.sh` |
| Look at an Orca terminal: idle, working, stopped on a prompt | `bash scripts/wait-for-agent.sh <handle> --once` |
| Show a desktop notification, optionally after a delay and only while a state-file line is unchanged | `python3 -I scripts/notify-desktop.py` |
| Kill what a browser-driving agent left behind | `bash scripts/cleanup-browsers.sh <scratch-dir>` |
| Screenshot a native popup the browser draws outside the page | `node scripts/capture-native-popup.js` |
| Measure a page against a design contract | `scripts/recon-extract.js`, `scripts/recon.sh` |
| Project facts, state of a ticket (spec, branch, PR) | `bash scripts/probe.sh` |
| Review delta since the last reviewed sha | `python3 -I scripts/review-delta.py` |
| Set, clear or show `outputStyle` in a project's, local or user settings file (other keys kept) | `python3 -I scripts/set-output-style.py` |
