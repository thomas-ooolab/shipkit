#!/usr/bin/env python3
"""PreToolUse hook: on Saturday and Sunday, block every tool call that sends something to other people.

Blocked at the weekend:
  - sending, editing or scheduling a Slack message
  - posting, editing or deleting a Jira comment
  - creating, commenting on, updating or merging a pull request
through shipkit's scripts (post-slack.js, jira-comment.py post|edit|delete, bitbucket-api.sh POST|PUT|DELETE, merge-pr.sh),
through a direct curl / gh call, and through the matching MCP tools. Reading is never blocked.

The day is the machine's local day; set SHIPKIT_TZ=<IANA zone> (e.g. Asia/Ho_Chi_Minh) in the environment Claude Code starts in
to use another zone. SHIPKIT_ALLOW_WEEKEND=1, set before Claude Code starts (an inline `VAR=1 cmd` in a command does not
count), lifts the block for that session.

stdin: the hook JSON (tool_name, tool_input). Exit 0 = allow; exit 2 = block, the reason on stderr goes back to the model.
Usage: python3 -I weekend-guard.py [--self-test]
"""
import datetime, importlib.util, json, os, re, sys

_spec = importlib.util.spec_from_file_location("common", os.path.join(os.path.dirname(os.path.abspath(__file__)), "common.py"))
common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common)

# A segment of a shell command is checked only when its first word is one of these — so `git commit -m "… post-slack.js …"`,
# `grep post-slack.js` or a heredoc line of message text never trips the guard.
RUNNERS = {"node", "python", "python3", "bash", "sh", "zsh", "curl", "gh"}

# (pattern on one segment, what it does). Edit this list to widen or narrow the guard.
SEGMENT_RULES = [
    (r"\bnode\s+\S*post-slack\.js(?!\s+--self-test)", "send or edit a Slack message"),
    (r"\bpython3?\s+(?:-\S+\s+)*\S*jira-comment\.py[\x22']?\s+(?:post|edit|delete)\b", "post, edit or delete a Jira comment"),
    (r"\bbash\s+\S*bitbucket-api\.sh[\x22']?\s+(?:POST|PUT|DELETE)\b", "write to Bitbucket (pull requests)"),
    (r"\bbash\s+\S*merge-pr\.sh\b", "merge a Bitbucket pull request"),
    (r"\bgh\s+pr\s+(?:create|merge|comment|review|edit|close|reopen)\b", "change a pull request"),
    (r"\bcurl\b.*\bslack\.com/api/(?:chat|files)\.", "call a Slack write API"),
]
WRITE_METHOD = re.compile(r"(?:-X|--request)\s*(?:POST|PUT|DELETE|PATCH)\b|\s-d\s|\s--data", re.I)
CURL_WRITE_TARGETS = [
    (r"api\.bitbucket\.org/\S*pullrequests", "write to Bitbucket (pull requests)"),
    (r"atlassian\.net/rest/api/\d+/issue/\S+/comment", "post, edit or delete a Jira comment"),
]
MCP_RULES = [
    (r"slack_send_message(?!_draft)|slack_schedule_message", "send a Slack message"),
    (r"addCommentToJiraIssue", "post a Jira comment"),
    (r"create_pull_request|merge_pull_request", "create or merge a pull request"),
]

def reason_for_bash(command):
    for seg, _words in common.segments(command, RUNNERS):
        for pat, what in SEGMENT_RULES:
            if re.search(pat, seg):
                return what
        if re.search(r"\bcurl\b", seg) and WRITE_METHOD.search(" " + seg):
            for pat, what in CURL_WRITE_TARGETS:
                if re.search(pat, seg):
                    return what
    return None

def reason(tool_name, tool_input):
    if tool_name == "Bash":
        return reason_for_bash((tool_input or {}).get("command", ""))
    if tool_name.startswith("mcp__"):
        for pat, what in MCP_RULES:
            if re.search(pat, tool_name):
                return what
    return None

def decide(tool_name, tool_input, now, env):
    """-> None to allow, else the message to show."""
    if env.get("SHIPKIT_ALLOW_WEEKEND") == "1" or not common.is_weekend(now):
        return None
    what = reason(tool_name, tool_input)
    if not what:
        return None
    return (f"shipkit weekend guard: blocked — {what} is not allowed on Saturday or Sunday ({now:%A %Y-%m-%d}). "
            "Nothing was sent. Draft it, keep it for Monday, and tell the user. "
            "(The user can lift this for a session with SHIPKIT_ALLOW_WEEKEND=1 in Claude Code's environment.)")

def self_test():
    sat, sun, mon, fri = (datetime.datetime(2026, 10, d, 12) for d in (17, 18, 19, 16))
    assert sat.weekday() == 5 and sun.weekday() == 6 and mon.weekday() == 0 and fri.weekday() == 4
    B = lambda c, now=sat, env={}: decide("Bash", {"command": c}, now, env)
    blocked = [
        "node \"${CLAUDE_PLUGIN_ROOT}/scripts/post-slack.js\" C1 - <<'EOF'\nhi\nEOF",
        "node scripts/post-slack.js edit C1 1.2 < new.txt",
        "cd /repo && python3 -I \"$R/scripts/jira-comment.py\" post AR-1 --file d.md",
        "python3 scripts/jira-comment.py edit AR-1 55 --file d.md",
        "python3 scripts/jira-comment.py delete AR-1 55",
        "bash -c 'bash scripts/merge-pr.sh ws repo 4'",
        "bash \"$P/skills/merge/merge-pr.sh\" ws repo 4",
        "bash scripts/bitbucket-api.sh POST /repositories/w/r/pullrequests body.json",
        "bash scripts/bitbucket-api.sh PUT /repositories/w/r/pullrequests/3 body.json",
        "curl -s -X POST -d @b.json https://api.bitbucket.org/2.0/repositories/w/r/pullrequests",
        "curl -X POST https://x.atlassian.net/rest/api/3/issue/AR-1/comment -d '{}'",
        "curl -s https://slack.com/api/chat.postMessage -d x",
        "FOO=1 gh pr create --fill",
    ]
    allowed = [
        "node scripts/post-slack.js --self-test",
        "python3 -I scripts/jira-comment.py --self-test",
        "python3 scripts/jira-comment.py assignable AR-1",
        "python3 scripts/jira-comment.py post AR-1 --dry-run" if False else "git commit -m \"run node scripts/post-slack.js\"",
        "grep -rn jira-comment.py post skills",
        "cat <<'EOF'\nnode scripts/post-slack.js C1\nEOF",
        "bash scripts/bitbucket-api.sh GET /repositories/w/r/pullrequests",
        "curl -s https://api.bitbucket.org/2.0/repositories/w/r/pullrequests",
        "curl -s https://x.atlassian.net/rest/api/3/issue/AR-1/comment",
        "gh pr view 3", "git push origin main", "ls",
    ]
    for c in blocked:
        assert B(c), f"should block on Saturday: {c!r}"
        assert B(c, sun), f"should block on Sunday: {c!r}"
        assert not B(c, mon) and not B(c, fri), f"must allow on a weekday: {c!r}"
        assert not B(c, env={"SHIPKIT_ALLOW_WEEKEND": "1"}), f"override: {c!r}"
    for c in allowed:
        assert not B(c), f"should allow on Saturday: {c!r}"
    M = lambda n, now=sat: decide(n, {}, now, {})
    for n in ("mcp__claude_ai_Slack__slack_send_message", "mcp__plugin_slack_slack__slack_schedule_message",
              "mcp__claude_ai_Atlassian__addCommentToJiraIssue", "mcp__plugin_ecc_github__create_pull_request",
              "mcp__plugin_ecc_github__merge_pull_request"):
        assert M(n) and not M(n, mon), n
    for n in ("mcp__claude_ai_Slack__slack_send_message_draft", "mcp__claude_ai_Slack__slack_read_thread",
              "mcp__claude_ai_Atlassian__getJiraIssue", "Read", "Edit"):
        assert not M(n), n
    print("weekend-guard: self-test ok")

def main():
    if "--self-test" in sys.argv:
        return self_test()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return  # not a hook payload — never block on a parse problem
    msg = decide(event.get("tool_name", ""), event.get("tool_input"), common.now_in(os.environ), os.environ)
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
