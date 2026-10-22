#!/usr/bin/env bash
# Kill what a browser-driving agent left behind: the node / shell processes whose working directory or command line is under the agent's
# scratch directory (parents first, so a chain.sh -> tail.sh -> rerun.sh loop cannot relaunch anything), their descendants, and the orphaned
# (PPID 1) chrome-headless-shell of ms-playwright that those scripts opened. Repeats until a scan finds nothing new.
# Never touches: this script and its ancestors, the user's Chrome, the Playwright MCP server or its browser, any process outside the directory.
#   usage: bash scripts/cleanup-browsers.sh <scratch-dir> [--dry-run]       (--dry-run lists and kills nothing)
#   exit 0 = done (or nothing to do) · 2 = bad usage / refused directory · 3 = something survived 20 passes
exec python3 -I - "$@" <<'PY'
import os, re, signal, subprocess, sys, time

SHELLS = {"node", "zsh", "bash", "sh", "dash"}
KEEP = ("@playwright/mcp", "playwright-mcp", "mcp-chrome")    # the MCP server and its browser are not ours to kill
ORPHAN = ("chrome-headless-shell", "ms-playwright")           # an orphaned headless shell of Playwright's own download
MAX_PASSES = 20

def table():  # pid -> (ppid, argv0 basename, command)
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout
    t = {}
    for line in out.splitlines():
        p = line.split(None, 2)
        if len(p) == 3 and p[0].isdigit() and p[1].isdigit():
            t[int(p[0])] = (int(p[1]), os.path.basename(p[2].split()[0]).lstrip("-"), p[2])
    return t

def cwds(pids):
    if not pids:
        return {}
    out = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fpn", "-p", ",".join(map(str, pids))], capture_output=True, text=True).stdout
    res, cur = {}, None
    for line in out.splitlines():
        if line.startswith("p"):
            cur = int(line[1:])
        elif line.startswith("n") and cur is not None:
            res[cur] = line[1:]
    return res

def under(path, d):
    return path == d or path.startswith(d + "/")

def mentions(cmd, *dirs):  # the directory as a whole path component: /x/a is in "node /x/a/run.cjs" but not in "node /x/ab/run.cjs"
    return any(re.search(re.escape(d) + r"(?![\w.\-])", cmd) for d in dirs)

def ancestors(pid, t):
    out = []
    while pid in t and t[pid][0] not in (0, 1) and t[pid][0] not in out:
        pid = t[pid][0]; out.append(pid)
    return out

def scan(d, raw, t, mine):
    """The pids to kill, parents before children."""
    keep = lambda cmd: any(k in cmd for k in KEEP)
    named = [pid for pid, (_, name, _) in t.items() if name in SHELLS and pid not in mine]
    cw = cwds(named)
    hit = {pid for pid in named
           if not keep(t[pid][2]) and (under(cw.get(pid, ""), d) or mentions(t[pid][2], d, raw))}
    for pid, (ppid, _, cmd) in t.items():                      # Playwright headless shells: orphaned, or opened under the directory
        if pid in mine or keep(cmd):
            continue
        if (all(w in cmd for w in ORPHAN) and ppid == 1) or ("chrome-headless-shell" in cmd and mentions(cmd, d, raw)):
            hit.add(pid)
    kids = {}
    for pid, (ppid, _, _) in t.items():
        kids.setdefault(ppid, []).append(pid)
    todo, seen = list(hit), set(hit)
    while todo:                                               # descendants of everything found
        for c in kids.get(todo.pop(), []):
            if c not in seen and c not in mine and not keep(t[c][2]):
                seen.add(c); todo.append(c)
    return sorted(seen, key=lambda pid: sum(1 for a in ancestors(pid, t) if a in seen))

def main():
    dry = "--dry-run" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) != 1:
        print("usage: cleanup-browsers.sh <scratch-dir> [--dry-run]", file=sys.stderr); return 2
    raw = args[0].rstrip("/")
    if not os.path.isdir(raw):
        print(f"cleanup-browsers: not a directory: {raw}", file=sys.stderr); return 2
    d = os.path.realpath(raw)
    if d in {"/", os.path.realpath(os.path.expanduser("~")), "/tmp", "/private/tmp", "/var/tmp", "/private/var/tmp", "/Users", "/home"} or d.count("/") < 2:
        print(f"cleanup-browsers: refusing {d}: too broad to be one agent's scratch directory", file=sys.stderr); return 2
    killed, passes = [], 0
    while passes < MAX_PASSES:
        t = table()
        mine = {os.getpid()} | set(ancestors(os.getpid(), t))
        found = scan(d, raw, t, mine)
        if not found:
            break
        for pid in found:
            ppid, name, cmd = t[pid]
            print(f"{'would kill' if dry else 'kill'} {pid} ppid={ppid} {name}: {cmd[:110]}")
        if dry:
            print(f"cleanup-browsers: {len(found)} process(es) would be killed (dry run)")
            return 0
        passes += 1
        for pid in found:                                      # freeze first: a stopped loop cannot relaunch anything
            try: os.kill(pid, signal.SIGSTOP)
            except OSError: pass
        for pid in found:
            try: os.kill(pid, signal.SIGKILL)
            except OSError: pass
        killed += found
        time.sleep(0.3)
    else:
        print(f"cleanup-browsers: something is still respawning under {d} after {MAX_PASSES} passes", file=sys.stderr); return 3
    print(f"cleanup-browsers: killed {len(killed)} process(es) in {passes} pass(es)" if killed else "cleanup-browsers: nothing to clean")
    return 0

sys.exit(main())
PY
