#!/usr/bin/env python3
"""next-workday.py — when /developer's next run is due: the next Monday-to-Friday start of the observer window, as a one-shot cron line.

  python3 -I scripts/next-workday.py --window 08:00-18:00 [--delay 3] [--tz Asia/Ho_Chi_Minh]
  python3 -I scripts/next-workday.py --self-test

Prints `<minute> <hour> <day> <month> * <ISO-8601 with offset>`: the first five fields are CronCreate's `cron` (the machine's local time, which is the
clock CronCreate reads), the last field is the same instant for the user to read. The instant is the window start plus --delay minutes (default 3: a
job that fires a minute or two early would find the window closed): today when today is a weekday and that moment is still ahead, otherwise the next
weekday. Never a Saturday or a Sunday. --tz (or SHIPKIT_TZ, else the machine's zone) is the zone the window is written in; the cron fields are
converted to the machine's zone.
Exit: 0 printed · 2 usage.
"""
import datetime, os, subprocess, sys

try:
    from zoneinfo import ZoneInfo
except ImportError:  # python < 3.9
    ZoneInfo = None


def zone(name):
    if name and ZoneInfo:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    return None


def next_run(now, start, delay):
    """The first weekday moment `start` + `delay` minutes that is after `now` (an aware datetime in the window's zone, or naive local)."""
    day = now.date()
    while True:
        at = datetime.datetime.combine(day, start, tzinfo=now.tzinfo) + datetime.timedelta(minutes=delay)
        if day.weekday() < 5 and at > now:
            return at
        day += datetime.timedelta(days=1)


def line(at):
    local = at.astimezone()  # a naive `at` is already local
    return f"{local.minute} {local.hour} {local.day} {local.month} * {local.isoformat(timespec='minutes')}"


def main(argv):
    a, window, delay, tz = list(argv), None, 3, os.environ.get("SHIPKIT_TZ")
    try:
        while a:
            x = a.pop(0)
            if x == "--window":
                window = a.pop(0)
            elif x == "--delay":
                delay = int(a.pop(0))
            elif x == "--tz":
                tz = a.pop(0)
            else:
                raise ValueError(x)
        start = datetime.time(int(window[:2]), int(window[3:5]))
    except (ValueError, IndexError, TypeError) as e:
        print(f"usage error: {e!r} (--window HH:MM-HH:MM [--delay MIN] [--tz ZONE])", file=sys.stderr)
        return 2
    print(line(next_run(datetime.datetime.now(zone(tz)), start, delay)))
    return 0


def self_test():
    z = ZoneInfo("Asia/Ho_Chi_Minh")
    s = datetime.time(8, 0)
    D = lambda d, h, m=0: datetime.datetime(2026, 11, d, h, m, tzinfo=z)   # 2026-11-16 is a Monday
    got = lambda now, delay=3: next_run(now, s, delay)
    assert got(D(19, 18, 2)) == D(20, 8, 3)        # Thursday evening -> Friday
    assert got(D(20, 18, 5)) == D(23, 8, 3)        # Friday evening -> Monday, not Saturday
    assert got(D(21, 10)) == D(23, 8, 3)           # Saturday -> Monday
    assert got(D(22, 23, 59)) == D(23, 8, 3)       # Sunday night -> Monday
    assert got(D(23, 7, 20)) == D(23, 8, 3)        # Monday before the start -> today
    assert got(D(23, 8, 1)) == D(23, 8, 3)         # two minutes before start+3 -> still today
    assert got(D(23, 8, 10)) == D(24, 8, 3)        # Monday after it -> Tuesday
    assert got(D(23, 7, 59), delay=0) == D(23, 8, 0)
    for d in range(16, 31):                        # the result is never a Saturday or a Sunday, whatever the day it is asked on
        for h in (0, 7, 8, 12, 18, 23):
            assert got(D(d, h)).weekday() < 5, (d, h)
    # cron fields are the machine's zone: the same instant under TZ=UTC is 01:03 (Vietnam is UTC+7), and the ISO field says so
    r = subprocess.run([sys.executable, "-I", __file__, "--window", "08:00-18:00", "--tz", "Asia/Ho_Chi_Minh"], capture_output=True, text=True,
                       env={**os.environ, "TZ": "UTC"})
    f = r.stdout.split()
    assert r.returncode == 0 and len(f) == 6 and f[0] == "3" and f[1] == "1" and f[4] == "*" and f[5].endswith("+00:00"), (r.stdout, r.stderr)
    assert main([]) == 2 and main(["--window"]) == 2 and main(["--window", "8am"]) == 2 and main(["--bogus"]) == 2
    print("next-workday self-test: ok")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main(sys.argv[1:]))
