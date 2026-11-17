#!/usr/bin/env python3
"""bugfix-coverage.py — has /bugfix checked every concern of the bug report? Read before an evidence comment goes out.

  python3 -I scripts/bugfix-coverage.py .shipkit/bugfix-<ticket>.md
  python3 -I scripts/bugfix-coverage.py --self-test

Reads the state file: the header line `concerns_in_report: <n>` (the concerns counted in the report itself, written when the report is
split) and the `## Concerns` list, one line per concern, `- [x|' '] <text> — <verdict>[: <detail>] [· <key>: <value>]…`. Verdicts:
`fixed on latest`, `still broken`, `fixed`, `changed, not reproduced`, `not a defect`, `needs decision`, `owned elsewhere`, `held`,
`not verifiable`. `unchecked` is no verdict. A concern is covered when its line has a verdict and every file named by `evidence:` or
`before:` exists (paths relative to the working directory, the worktree root). Prints `coverage: <covered>/<n> · fixed on latest <a> ·
still broken <b> · other <c>` and then `all-fixed-on-latest` (every concern is `fixed on latest`), `partial` or `none`.
Exit: 0 every concern covered (the verdict line follows) · 1 not covered, each reason on stderr · 2 usage or no `concerns_in_report:`.
"""
import os, re, subprocess, sys, tempfile

VERDICTS = ("fixed on latest", "still broken", "fixed", "changed, not reproduced", "not a defect", "needs decision",
            "owned elsewhere", "held", "not verifiable")
LINE = re.compile(r"^- \[[ xX]\] (.*)$")
VERDICT = re.compile(r" — (" + "|".join(re.escape(v) for v in VERDICTS) + r")(?!\w)")
FILES = re.compile(r"\b(?:evidence|before):\s*([^·]*)")   # every path up to the next " · " (or the end of the line)


def check(text, root="."):
    """-> (n reported or None, [(concern, verdict or None)], [reasons it is not covered])"""
    m = re.search(r"^concerns_in_report:\s*(\d+)\s*$", text, re.M)
    if not m:
        return None, [], ["no `concerns_in_report: <n>` line"]
    n, rows, why = int(m.group(1)), [], []
    sec = re.split(r"^## Concerns.*$", text, maxsplit=1, flags=re.M)
    for ln in (re.split(r"^## ", sec[1], maxsplit=1, flags=re.M)[0] if len(sec) > 1 else "").splitlines():
        lm = LINE.match(ln)
        if not lm:
            continue
        v = VERDICT.search(lm.group(1))
        rows.append((lm.group(1)[:60], v.group(1) if v else None))
        if not v:
            why.append(f"no verdict: {lm.group(1)[:60]}")
        for chunk in FILES.findall(lm.group(1)):
            for f in (t for t in re.split(r"[\s,;]+", chunk) if re.search(r"\.\w{2,5}$", t)):
                if not os.path.isfile(os.path.join(root, f)):
                    why.append(f"evidence file missing: {f}")
    if len(rows) != n:
        why.append(f"{len(rows)} concern line(s) but the report has {n}")
    return n, rows, why


def main(argv):
    if len(argv) != 1 or argv[0].startswith("-"):
        print("usage: bugfix-coverage.py <state file> | --self-test", file=sys.stderr)
        return 2
    try:
        text = open(argv[0], encoding="utf-8").read()
    except OSError as e:
        print(f"usage error: {e}", file=sys.stderr)
        return 2
    n, rows, why = check(text)
    if n is None:
        print(why[0], file=sys.stderr)
        return 2
    count = lambda v: sum(1 for _, x in rows if x == v)
    covered = sum(1 for _, x in rows if x)
    a, b = count("fixed on latest"), count("still broken")
    for w in why:
        print(w, file=sys.stderr)
    if why:
        print(f"coverage: {covered}/{n} · NOT covered", file=sys.stderr)
        return 1
    print(f"coverage: {covered}/{n} · fixed on latest {a} · still broken {b} · other {covered - a - b}")
    print("all-fixed-on-latest" if a == n else "partial" if a + count("fixed") else "none")
    return 0


def self_test():
    d = tempfile.mkdtemp()
    for f in ("1-after.png", "2-before.png"):
        open(os.path.join(d, f), "w").close()
    head = "# Bugfix loop state — AR-1\nconcerns_in_report: {n}\n\n## Concerns\n"
    ok1 = "- [x] digest counts a call once per attendee — fixed on latest · fixing change: AR-871 71aa001 (digest.go:88) · evidence: 1-after.png\n"
    bad2 = "- [ ] call list shows pre-join calls — still broken · before: 2-before.png\n"
    run = lambda body, n: check(head.format(n=n) + body, d)
    two = ok1.replace("evidence: 1-after.png", "evidence: 1-after.png, 9-after.txt")          # a second path on the same line is checked too
    assert any("9-after.txt" in w for w in run(two, 1)[2])
    assert run(ok1.replace("evidence: 1-after.png", "evidence: 1-after.png 2-before.png"), 1)[2] == []
    assert run(ok1, 1)[2] == []                                                     # one concern, covered
    assert run(ok1 + bad2, 2)[2] == []                                             # two, covered
    assert "1 concern line(s) but the report has 2" in run(ok1, 2)[2]               # a concern of the report with no line
    assert any("no verdict" in w for w in run(ok1 + "- [ ] export is greyed out for admins\n", 2)[2])
    assert any("no verdict" in w for w in run(ok1 + "- [ ] export is greyed out — unchecked\n", 2)[2])
    assert any("missing" in w for w in run(ok1.replace("1-after.png", "9-after.png"), 1)[2])   # evidence named but not on disk
    assert run("- [ ] x — not verifiable: no staging login\n", 1)[2] == []          # a blocker is a verdict, it is not "all fixed"
    assert check("# no header\n## Concerns\n- [x] a — fixed on latest\n", d)[0] is None
    assert run("- [x] a — fixed, fix/AR-1-x, verified: PASS\n- [ ] b — not a defect (awaiting reporter ack)\n", 2)[2] == []
    p = os.path.join(d, "s.md")
    for body, n, rc, last in ((ok1, 1, 0, "all-fixed-on-latest"), (ok1 + bad2, 2, 0, "partial"), (bad2, 1, 0, "none"), (ok1, 2, 1, None)):
        open(p, "w").write(head.format(n=n) + body)
        r = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), p], capture_output=True, text=True, cwd=d)
        assert r.returncode == rc and (last is None or r.stdout.splitlines()[-1] == last), (body, r.returncode, r.stdout, r.stderr)
    assert main([]) == 2 and main(["/nonexistent/x.md"]) == 2
    print("bugfix-coverage self-test: ok")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main(sys.argv[1:]))
