#!/usr/bin/env python3
"""PreToolUse hook: `git push` is allowed only from 08:00 to 18:00, Monday to Friday — at any other time it is blocked, commit only.

Why: a push late in the evening notifies people (Slack, e-mail, pipelines) after hours. Committing locally stays allowed.
How: any `git push` in a Bash command (also after `cd`, `git -C`, inside `bash -c`) is blocked, whatever branch or remote.
Outside the window means before 08:00, from 18:00 on, and all of Saturday and Sunday (pr-branch-guard.py still covers PR branches there).

The clock is the machine's local time; set SHIPKIT_TZ=<IANA zone> (e.g. Asia/Ho_Chi_Minh) in the environment Claude Code starts
in to use another zone. SHIPKIT_ALLOW_AFTER_HOURS=1, set before Claude Code starts (an inline `VAR=1 cmd` does not count),
lifts the block for that session.
Not covered: pushes through an MCP tool, and anything the user types in their own terminal.

stdin: the hook JSON (tool_name, tool_input). Exit 0 = allow; exit 2 = block, the reason on stderr goes to the model.
Usage: python3 -I after-hours-push-guard.py [--self-test]
"""
import datetime, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

common = load("common", "common.py")
parse_push = load("pr_branch_guard", "pr-branch-guard.py").parse_push

OPEN_HOUR, CLOSE_HOUR = 8, 18  # 08:00 sharp is allowed, 18:00 sharp is already blocked

def decide(command, now, env):
    """-> None to allow, else the message to show."""
    if env.get("SHIPKIT_ALLOW_AFTER_HOURS") == "1" or (now.weekday() < 5 and OPEN_HOUR <= now.hour < CLOSE_HOUR):
        return None
    for _seg, words in common.segments(command, {"git"} | common.SHELLS):  # shells: segments() looks inside `bash -c '…'`
        if os.path.basename(words[0]) == "git" and parse_push(words):
            return (f"shipkit after-hours push guard: blocked — `git push` is only allowed {OPEN_HOUR:02d}:00-{CLOSE_HOUR:02d}:00 Monday to Friday "
                    f"(now {now:%A %H:%M}). Commit locally, do not push, and tell the user it is ready to push. "
                    "(The user can lift this for a session with SHIPKIT_ALLOW_AFTER_HOURS=1 in Claude Code's environment.)")
    return None

def self_test():
    at = lambda day, h, m=0: datetime.datetime(2026, 10, day, h, m)  # 19 = Mon … 23 = Fri, 24 = Sat
    assert at(19, 0).weekday() == 0 and at(23, 0).weekday() == 4 and at(24, 0).weekday() == 5
    D = lambda c, now=at(21, 20), env={}: decide(c, now, env)  # Wed 20:00, outside the window
    for c in ["git push", "git push origin main", "git push -u origin HEAD", "git -C sub push --force-with-lease origin x",
              "cd sub && git push", "git add . && git commit -m x && git push", "bash -c 'git push origin main'",
              "git push --delete origin old", "git push --tags"]:
        assert D(c), c
    for c in ["git commit -m 'git push later'", "git status", "git pull", "echo git push", "grep 'git push' README.md", "git stash push", "bash push.sh"]:
        assert not D(c), c  # never a push, so never blocked
    assert D("git push", at(19, 18, 0)) and D("git push", at(23, 23, 59))      # Mon 18:00 and Fri 23:59 blocked
    assert D("git push", at(19, 7, 59)) and D("git push", at(19, 0))           # before 08:00 blocked
    assert not D("git push", at(19, 8, 0)) and not D("git push", at(23, 17, 59))  # Mon 08:00 .. Fri 17:59 allowed
    assert D("git push", at(24, 12)) and D("git push", at(25, 12))             # Saturday / Sunday blocked all day
    assert not D("git push", env={"SHIPKIT_ALLOW_AFTER_HOURS": "1"})
    print("after-hours-push-guard: self-test ok")

def main():
    if "--self-test" in sys.argv:
        return self_test()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if event.get("tool_name") != "Bash":
        return
    msg = decide((event.get("tool_input") or {}).get("command", ""), common.now_in(os.environ), os.environ)
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
