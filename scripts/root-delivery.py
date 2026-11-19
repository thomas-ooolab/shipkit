#!/usr/bin/env python3
"""root-delivery.py — was a message to the root coordinator (run:<RUN>) delivered; when not, wake the root only when that is safe.

  python3 -I scripts/root-delivery.py --run <RUN> --msg <message id> --terminal <root_terminal> [--nudged]
  python3 -I scripts/root-delivery.py --self-test

Orca delivers mail to a run by typing a wake line into its terminal, and a delivery can come minutes late with the root idle
(AR-678, 2026-11-19: 9 min 23 s, root at an empty input box the whole time). The cause is not known, so this does not depend on it.

1. `orca orchestration inbox --terminal run:<RUN> --full --json`: the message's `delivered_at` is set -> DELIVERED.
2. Else read the root terminal (scripts/wait-for-agent.sh <terminal> --once, which only reads). Only when the screen says the agent is
   idle AND its input box between the two rules is empty, type Orca's own wake line and Enter -> NUDGED.
   A root that is mid-turn, stopped on a prompt, or has text in its input box gets nothing typed (a broadcast once landed in a
   half-typed /merge command) -> RETRY. A placeholder or suggestion drawn in the box reads as text: no nudge, never a guess.
3. `--nudged` (the caller already woke this message once): never types again -> RETRY.

stdout, one line:  DELIVERED <delivered_at> | NUDGED | RETRY <reason> | ERROR <reason>
exit 0 DELIVERED or NUDGED · 10 RETRY (read again in 2-3 minutes) · 4 ERROR (orca failed, message not in that inbox) · 2 usage.
ORCA is resolved like wait-for-agent.sh (ORCA_CLI_COMMAND, ORCA_DEV_REPO_ROOT, Linux orca-ide, else orca).
"""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT_ROWS = "500"


def orca_cmd():
    if os.environ.get("ORCA_CLI_COMMAND"):
        return os.environ["ORCA_CLI_COMMAND"]
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        return "orca-dev"
    return "orca-ide" if sys.platform.startswith("linux") else "orca"


def orca(*args):
    p = subprocess.run([orca_cmd(), *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def box_is_empty(lines):
    """True when the last input box (two rules, at most 6 lines apart) holds no text after its prompt mark; None when no box is found."""
    rules = [i for i, l in enumerate(lines) if re.search(r"[─━]{8,}", l)]
    for a, b in reversed(list(zip(rules, rules[1:]))):
        if 1 <= b - a <= 7:
            inner = [l.strip() for l in lines[a + 1:b]]
            return all(re.fullmatch(r"[❯>›]?", l) for l in inner)
    return None


def check(run, msg, terminal, nudged):
    rc, out, err = orca("orchestration", "inbox", "--terminal", f"run:{run}", "--full", "--limit", LIMIT_ROWS, "--json")
    try:
        rows = json.loads(out)["result"]["messages"]
    except Exception:
        return 4, f"ERROR inbox of run:{run} not readable (orca exit {rc})"
    row = next((m for m in rows if m.get("id") == msg), None)
    if row is None:
        return 4, f"ERROR message {msg} is not in the inbox of run:{run}"
    if row.get("delivered_at"):
        return 0, f"DELIVERED {row['delivered_at']}"
    if nudged:
        return 10, "RETRY already woken once, nothing typed"
    p = subprocess.run(["bash", str(HERE / "wait-for-agent.sh"), terminal, "--once"], capture_output=True, text=True, env=os.environ)
    first, _, rest = p.stdout.partition("\n")
    if first != "SCREEN=agent":
        return 10, f"RETRY root terminal is {first.replace('SCREEN=', '') or 'unreadable'}, nothing typed"
    empty = box_is_empty(rest.splitlines()[1:])
    if empty is not True:
        return 10, "RETRY input box is not empty or not found, nothing typed"
    wake = f"You have 1 orchestration message. Run orca orchestration check --run {run}."
    rc, _, _ = orca("terminal", "send", "--terminal", terminal, "--text", wake, "--enter")
    return (0, "NUDGED") if rc == 0 else (4, f"ERROR terminal send failed (orca exit {rc})")


def main(argv):
    if argv == ["--self-test"]:
        return self_test()
    a, opt, nudged = list(argv), {}, False
    while a:
        k = a.pop(0)
        if k == "--nudged":
            nudged = True
        elif k in ("--run", "--msg", "--terminal") and a:
            opt[k] = a.pop(0)
        else:
            print(__doc__.split("\n\n")[0], file=sys.stderr)
            return 2
    if set(opt) != {"--run", "--msg", "--terminal"}:
        print("usage: root-delivery.py --run <RUN> --msg <id> --terminal <root_terminal> [--nudged]", file=sys.stderr)
        return 2
    code, line = check(opt["--run"], opt["--msg"], opt["--terminal"], nudged)
    print(line)
    return code


STUB = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
d = os.environ["STUB_DIR"]
if a[:2] == ["orchestration", "inbox"]:
    rows = json.load(open(d + "/inbox.json"))
    print(json.dumps({"ok": True, "result": {"messages": rows, "count": len(rows)}}))
elif a[:2] == ["terminal", "read"]:
    print(json.dumps({"ok": True, "result": {"terminal": {"status": "running", "tail": json.load(open(d + "/screen.json"))}}}))
elif a[:2] == ["terminal", "send"]:
    open(d + "/sent.txt", "a").write(json.dumps(a) + "\n")
else:
    sys.exit(9)
'''
RULE = "─" * 40


def self_test():
    ok = True

    def case(label, rows, screen, want_line, want_code, want_sent, extra=()):
        nonlocal ok
        with tempfile.TemporaryDirectory() as d:
            Path(d, "orca").write_text(STUB)
            os.chmod(Path(d, "orca"), 0o755)
            Path(d, "inbox.json").write_text(json.dumps(rows))
            Path(d, "screen.json").write_text(json.dumps(screen))
            env = {**os.environ, "ORCA_CLI_COMMAND": str(Path(d, "orca")), "STUB_DIR": d}
            p = subprocess.run([sys.executable, "-I", __file__, "--run", "run_1", "--msg", "m1", "--terminal", "t1", *extra],
                               capture_output=True, text=True, env=env)
            sent = Path(d, "sent.txt").read_text().strip().splitlines() if Path(d, "sent.txt").exists() else []
            good = p.stdout.startswith(want_line) and p.returncode == want_code and len(sent) == want_sent
            if good and want_sent:
                s = json.loads(sent[0])
                good = "--enter" in s and s[s.index("--text") + 1] == "You have 1 orchestration message. Run orca orchestration check --run run_1."
            print(("ok    " if good else "FAIL  ") + label + ("" if good else f"  got {p.stdout.strip()!r} exit {p.returncode} sent {len(sent)} {p.stderr.strip()[:200]}"))
            ok = ok and good

    undelivered = [{"id": "m0", "delivered_at": "t"}, {"id": "m1", "delivered_at": None}]
    idle = ["• done", RULE, "❯ ", RULE, "  ⏵⏵ accept edits on"]
    case("delivered: nothing typed", [{"id": "m1", "delivered_at": "2026-11-19T08:51:54Z"}], idle, "DELIVERED 2026-11-19T08:51:54Z", 0, 0)
    case("undelivered, idle empty box: wake line typed", undelivered, idle, "NUDGED", 0, 1)
    case("undelivered, text in the box: nothing typed", undelivered, ["• done", RULE, "❯ /merge AR-6", RULE], "RETRY input box", 10, 0)
    case("undelivered, placeholder in the box reads as text", undelivered, ["• done", RULE, "❯ Try \"fix lint errors\"", RULE], "RETRY input box", 10, 0)
    case("undelivered, root mid-turn: nothing typed", undelivered, ["✢ Working… (12s · esc to interrupt)", RULE, "❯ ", RULE], "RETRY root terminal is working", 10, 0)
    case("undelivered, root on a y/n prompt: nothing typed", undelivered, ["Do you want to proceed? (y/n)"], "RETRY root terminal is attention", 10, 0)
    case("undelivered, already nudged: nothing typed", undelivered, idle, "RETRY already woken", 10, 0, ("--nudged",))
    case("message not in the inbox", [{"id": "other", "delivered_at": None}], idle, "ERROR message m1 is not in the inbox", 4, 0)
    print("root-delivery.py self-test:", "all ok" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
