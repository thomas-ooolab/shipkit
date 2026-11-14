#!/usr/bin/env python3
"""notify-desktop.py — show a desktop notification, optionally after a delay and only if a state-file line is unchanged.

  python3 -I scripts/notify-desktop.py --title T --message M
  python3 -I scripts/notify-desktop.py --after 14400 --window 08:00-18:00 \
      --unless-changed .shipkit/pipeline-AR-1.md "Waiting since:" "2026-11-16T09:00:00Z" --title T --message M
  python3 -I scripts/notify-desktop.py --print ...     # show what would be sent, send nothing
  python3 -I scripts/notify-desktop.py --self-test

--after S             sleep S seconds first (run it with Bash run_in_background: the task ending is the signal).
--window HH:MM-HH:MM  the notice is only shown inside this window (local time, or SHIPKIT_TZ=<IANA zone>); fired outside it, wait for the next start.
--unless-changed F P V  after the sleep read file F: when its line starting with P no longer reads "P V" (the cause was resolved, the file or the line is gone) exit 0
                      without notifying. Used by /run-pipeline: a notice for "Waiting since: <ISO>" is dropped once the stage moved on.
Title and message are passed to the OS as separate arguments, never put into a shell string, so Jira text in them cannot run anything.
macOS: osascript. Linux: notify-send. Otherwise exit 3.
Exit: 0 shown, or dropped by --unless-changed · 2 usage · 3 no notifier on this system · 4 the notifier failed.
"""
import datetime, os, subprocess, sys, tempfile, time
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # python < 3.9
    ZoneInfo = None


def now():
    tz = os.environ.get("SHIPKIT_TZ")
    if tz and ZoneInfo:
        try:
            return datetime.datetime.now(ZoneInfo(tz))
        except Exception:
            pass
    return datetime.datetime.now()


def parse_window(text):
    a, b = text.split("-")
    f = lambda s: datetime.time(int(s[:2]), int(s[3:5]))
    return f(a), f(b)


def seconds_to_window(at, start, end):
    """0 when `at` is inside [start, end), else the seconds until the next start."""
    t = at.time()
    if start <= t < end:
        return 0
    day = at.date() if t < start else at.date() + datetime.timedelta(days=1)
    nxt = datetime.datetime.combine(day, start, tzinfo=at.tzinfo)
    return max(1, int((nxt - at).total_seconds()))


def line_unchanged(path, prefix, value):
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith(prefix):
                return line[len(prefix):].strip() == value
    except OSError:
        return False
    return False


def notifier(title, message):
    if sys.platform == "darwin":
        return ["osascript", "-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)", "-e", "end run", title, message]
    if subprocess.run(["which", "notify-send"], capture_output=True).returncode == 0:
        return ["notify-send", title, message]
    return None


def main(argv):
    a = list(argv)
    after, window, unless, title, message, dry = 0, None, None, None, None, False
    try:
        while a:
            x = a.pop(0)
            if x == "--after":
                after = int(a.pop(0))
            elif x == "--window":
                window = parse_window(a.pop(0))
            elif x == "--unless-changed":
                unless = (a.pop(0), a.pop(0), a.pop(0))
            elif x == "--title":
                title = a.pop(0)
            elif x == "--message":
                message = a.pop(0)
            elif x == "--print":
                dry = True
            elif x in ("-h", "--help"):
                print(__doc__); return 0
            else:
                raise ValueError(x)
    except (ValueError, IndexError) as e:
        print(f"usage error: {e} (try --help)", file=sys.stderr); return 2
    if not title or message is None:
        print("--title and --message are required (try --help)", file=sys.stderr); return 2
    if after > 0 and not dry:
        time.sleep(after)
    if window and not dry:
        while True:
            wait = seconds_to_window(now(), *window)
            if wait == 0:
                break
            time.sleep(min(wait, 3600))
    if unless and not line_unchanged(*unless):
        return 0
    cmd = notifier(title, message)
    if dry:
        print("would notify:", cmd if cmd else "no notifier on this system"); return 0
    if cmd is None:
        print("no desktop notifier on this system (macOS osascript or Linux notify-send)", file=sys.stderr); return 3
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"notifier failed: {r.stderr.strip()}", file=sys.stderr); return 4
    return 0


def self_test():
    D = lambda h, m=0, day=16: datetime.datetime(2026, 11, day, h, m)
    s, e = parse_window("08:00-18:00")
    assert seconds_to_window(D(9), s, e) == 0 and seconds_to_window(D(17, 59), s, e) == 0
    assert seconds_to_window(D(18), s, e) == 14 * 3600 and seconds_to_window(D(7, 30), s, e) == 1800   # next 08:00
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "pipeline-AR-1.md"
        f.write_text("# x\nWaiting since: 2026-11-16T09:00:00Z\nStatus: waiting-user · x\n")
        assert line_unchanged(f, "Waiting since:", "2026-11-16T09:00:00Z")
        assert not line_unchanged(f, "Waiting since:", "2026-11-17T09:00:00Z")      # the cause changed
        assert not line_unchanged(f, "Nope:", "x") and not line_unchanged(Path(d) / "gone.md", "Waiting since:", "x")
        # --unless-changed with a changed line: exit 0, nothing shown, no sleep
        assert main(["--unless-changed", str(f), "Waiting since:", "other", "--title", "t", "--message", "m"]) == 0
        # --print never notifies; a message with quotes and $() is just data
        assert main(["--print", "--title", "t", "--message", "it's $(rm -rf /) \"x\""]) == 0
    assert main([]) == 2 and main(["--after"]) == 2 and main(["--bogus"]) == 2 and main(["--title", "t"]) == 2
    cmd = notifier("a", "b'c")
    assert cmd is None or "b'c" in cmd       # passed as its own argv item
    print("notify-desktop self-test: ok")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main(sys.argv[1:]))
