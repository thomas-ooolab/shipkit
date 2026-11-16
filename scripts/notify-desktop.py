#!/usr/bin/env python3
"""notify-desktop.py — show a desktop notification, optionally after a delay and only if a state-file line is unchanged.

  python3 -I scripts/notify-desktop.py --title T --message M
  python3 -I scripts/notify-desktop.py --after 14400 --window 08:00-18:00 \
      --unless-changed .shipkit/pipeline-AR-1.md "Waiting since:" "2026-11-16T09:00:00Z" --title T --message M
  python3 -I scripts/notify-desktop.py --wait-only --after 7200 \
      --unless-changed .shipkit/pipeline-AR-1.md "Waiting since:" "2026-11-16T09:00:00Z"
  python3 -I scripts/notify-desktop.py --print ...     # show what would be sent, send nothing
  python3 -I scripts/notify-desktop.py --self-test

--after S             sleep S seconds first (run it with Bash run_in_background: the task ending is the signal).
--window HH:MM-HH:MM  the notice is only shown inside this window (local time, or SHIPKIT_TZ=<IANA zone>); fired outside it, wait for the next start.
--unless-changed F P V  read file F every minute while sleeping (--after and the --window wait) and once more before notifying: when its line starting
                      with P no longer reads "P V" (the cause was resolved, the file or the line is gone) exit 0 at once without notifying, so the
                      process ends within about a minute of the change. Used by /run-pipeline: a notice for "Waiting since: <ISO>" is dropped
                      as soon as the stage moved on.
--wait-only           no notice: just wait --after S (with --unless-changed, as above) and end. A timer that wakes a session without a person:
                      a blind `sleep` outlives its cause, this one ends within about a minute of it. Takes no --window, --title or --message.
                      The --unless-changed line must be there when it starts (the timer is armed right after the line is written): a missing file,
                      a wrong working directory for a relative path or a wrong prefix exits 2 at once instead of passing for "the cause is gone".
Title and message are passed to the OS as separate arguments, never put into a shell string, so Jira text in them cannot run anything.
macOS: osascript. Linux: notify-send. Otherwise exit 3.
Exit: 0 shown, or dropped by --unless-changed; with --wait-only: the time ran out · 2 usage (--wait-only: also a line that is not there at the start) · 3 no notifier on this system · 4 the notifier failed ·
      5 --wait-only only: the --unless-changed line changed first (the cause is gone: nothing is left to do on the wake).
"""
import datetime, os, re, subprocess, sys, tempfile, threading, time
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


STEP, RECHECK = 60, 2   # seconds: how often a wait looks at the --unless-changed line; the pause before a change is confirmed


def wait(seconds, unless):
    """Sleep `seconds` in steps of at most STEP. False as soon as the --unless-changed line has changed (looked at before every step),
    so a notice whose cause is resolved ends within a minute, not after the whole delay. A change is confirmed RECHECK seconds later,
    because a state file being rewritten can read as a missing line for an instant."""
    end = time.monotonic() + seconds
    while True:
        if unless and not line_unchanged(*unless):
            time.sleep(RECHECK)
            if not line_unchanged(*unless):
                return False
        left = end - time.monotonic()
        if left <= 0:
            return True
        time.sleep(min(STEP, left))


def notifier(title, message):
    if sys.platform == "darwin":
        return ["osascript", "-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)", "-e", "end run", title, message]
    if subprocess.run(["which", "notify-send"], capture_output=True).returncode == 0:
        return ["notify-send", title, message]
    return None


def main(argv):
    a = list(argv)
    after, window, unless, title, message, dry, wait_only = 0, None, None, None, None, False, False
    try:
        while a:
            x = a.pop(0)
            if x == "--wait-only":
                wait_only = True
            elif x == "--after":
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
    if wait_only:
        if after <= 0 or window or title or message is not None:
            print("--wait-only takes --after (and --unless-changed) only (try --help)", file=sys.stderr); return 2
        if dry:
            print(f"would wait {after} s"); return 0
        if unless and not line_unchanged(*unless):   # a timer is armed right after the line is written: not there now means a wrong path, cwd or prefix
            print(f"line not found at start: {unless[0]} {unless[1]!r} {unless[2]!r} (a relative file path needs the worktree root as the working directory)", file=sys.stderr)
            return 2
        return 0 if wait(after, unless) else 5
    if not title or message is None:
        print("--title and --message are required (try --help)", file=sys.stderr); return 2
    if after > 0 and not dry and not wait(after, unless):
        return 0
    if window and not dry:
        while True:
            to_start = seconds_to_window(now(), *window)
            if to_start == 0:
                break
            if not wait(min(to_start, 3600), unless):
                return 0
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
        # a wait ends within seconds of the change, however long it was asked to sleep (the bug: it slept the whole --after)
        global STEP, RECHECK
        STEP, RECHECK = 1, 0.2
        f.write_text("# x\nWaiting since: 2026-11-16T09:00:00Z\nStatus: waiting-user · x\n")
        unless = (str(f), "Waiting since:", "2026-11-16T09:00:00Z")
        t0 = time.monotonic()
        assert wait(2, unless) is True and 1.5 < time.monotonic() - t0 < 6      # unchanged line: sleeps its time, then goes on to notify
        threading.Timer(1.5, lambda: f.write_text("# x\nStatus: done\n")).start()   # the stage moved on: the line is gone
        t0 = time.monotonic()
        assert main(["--after", "3600", "--unless-changed", *unless, "--title", "t", "--message", "m"]) == 0
        assert time.monotonic() - t0 < 10, "slept through a changed line"
        t0 = time.monotonic()                                                     # the same while waiting for the window (never inside 00:00-00:00)
        assert main(["--window", "00:00-00:00", "--unless-changed", *unless, "--title", "t", "--message", "m"]) == 0
        assert time.monotonic() - t0 < 10, "slept through a changed line in the window wait"
        # --wait-only: the timers of loop-rules §8, §9 and the push window. 0 when the time ran out, 5 when the line changed first
        t0 = time.monotonic()
        # a line that is not there at the start is a wrong path, cwd or prefix, not "the cause is gone": exit 2 at once, never a silent 5
        assert main(["--wait-only", "--after", "3600", "--unless-changed", *unless]) == 2 and time.monotonic() - t0 < 10   # the file has no such line now
        assert main(["--wait-only", "--after", "3600", "--unless-changed", str(Path(d) / "no-such-dir" / "p.md"), "Waiting since:", "x"]) == 2
        f.write_text("# x\nWaiting since: 2026-11-16T09:00:00Z\n")
        assert main(["--wait-only", "--after", "3600", "--unless-changed", str(f), "Waiting sine:", "2026-11-16T09:00:00Z"]) == 2    # a typo in the prefix
        assert time.monotonic() - t0 < 10
        f.write_text("# x\nWaiting since: 2026-11-16T09:00:00Z\nStatus: waiting-user · x\n")
        t0 = time.monotonic()
        assert main(["--wait-only", "--after", "2", "--unless-changed", *unless]) == 0 and 1.5 < time.monotonic() - t0 < 6
        threading.Timer(1.5, lambda: f.write_text("# x\nStatus: running\n")).start()      # the answer arrives while it waits
        t0 = time.monotonic()
        assert main(["--wait-only", "--after", "3600", "--unless-changed", *unless]) == 5 and time.monotonic() - t0 < 10
        assert main(["--wait-only", "--after", "5", "--print"]) == 0                      # shows, waits for nothing
        assert main(["--wait-only"]) == 2 and main(["--wait-only", "--after", "5", "--window", "08:00-18:00"]) == 2
        assert main(["--wait-only", "--after", "5", "--title", "t", "--message", "m"]) == 2
        # the push-window loop of loop-rules §7, taken from the text and run for real: it ends with the script's own exit code, so 5 means
        # "the line changed" and nothing else does (a loop that said `|| exit 5` turned a usage error into a silent no-op)
        root = Path(__file__).resolve().parent.parent
        doc = next(l for l in (root / "skills/run-pipeline/loop-rules.md").read_text().splitlines() if "closed push window wakes itself" in l)
        loop = re.search(r"bash -c '(until .*? done)'", doc).group(1)
        fake = Path(d) / "plugin"
        (fake / "hooks").mkdir(parents=True)
        (fake / "scripts").mkdir()
        (fake / "scripts" / "notify-desktop.py").symlink_to(Path(__file__).resolve())
        # the push guard's stand-in: window closed (0 minutes left) the first time it is asked, open (30) after that
        (fake / "hooks" / "after-hours-push-guard.py").write_text(
            "import pathlib\np = pathlib.Path(__file__).with_name('n')\nn = int(p.read_text()) if p.exists() else 0\np.write_text(str(n + 1))\nprint(0 if n == 0 else 30)\n")
        (Path(d) / ".shipkit").mkdir()
        state = Path(d) / ".shipkit" / "pipeline-T-1.md"

        def run_loop(after, line_present=True, drop_after=None):
            state.write_text("# x\nWaiting since: 2026-11-16T09:00:00Z\n" if line_present else "# x\nStatus: running\n")
            if drop_after:                                                      # the answer arrives while the loop waits
                threading.Timer(drop_after, lambda: state.write_text("# x\nStatus: running\n")).start()
            (fake / "hooks" / "n").unlink(missing_ok=True)
            cmd = loop.replace("<ticket>", "T-1").replace("<the ISO written>", "2026-11-16T09:00:00Z").replace("--after 300", f"--after {after}")
            r = subprocess.run(["bash", "-c", cmd], cwd=d, capture_output=True, text=True, timeout=60,
                               env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(fake)})
            return r.returncode, r.stderr
        assert run_loop(1, True)[0] == 0           # the time ran out, the window is open: the loop ends 0 (wake and carry on)
        assert run_loop(3, drop_after=0.5)[0] == 5  # the line goes while it waits: the script's own 5
        rc, err = run_loop(1, line_present=False)   # the line was never there (wrong path or prefix): a failure of the timer, not a 5
        assert rc == 2 and "line not found at start" in err, (rc, err)
        rc, err = run_loop(0, True)                # --after 0 is a usage error of the script: its 2 comes out, not 5
        assert rc == 2 and "--wait-only takes" in err, (rc, err)
    assert main([]) == 2 and main(["--after"]) == 2 and main(["--bogus"]) == 2 and main(["--title", "t"]) == 2
    cmd = notifier("a", "b'c")
    assert cmd is None or "b'c" in cmd       # passed as its own argv item
    print("notify-desktop self-test: ok")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main(sys.argv[1:]))
