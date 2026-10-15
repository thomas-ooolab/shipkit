#!/usr/bin/env python3
"""Fail when a file that restates the pipeline order drifts from skills/run-pipeline/stages.txt.

Usage: python3 -I scripts/check-pipeline.py [--self-test]      exit 0 ok · 1 drift · 2 missing file/anchor
Checks only skill names and their order (and that the required ones are present), not wording —
a stale sentence like "verify posts to Jira" is still on the person changing the pipeline.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = [l.split() for l in (ROOT / "skills/run-pipeline/stages.txt").read_text().splitlines()
          if l.strip() and not l.startswith("#")]
RANK = {n: i for i, g in enumerate(GROUPS) for n in g}

# (file, region start regex, region end regex or None = start line only, required skills)
# ponytail: run-pipeline has no clarify / plan-deep stage yet — add them to its required list when it gets one.
CHECKS = [
    ("skills/run-pipeline/SKILL.md", r"^## Stages", r"^```", ["spec-from-ticket", "review-changes", "verify", "pr", "bump-submodule"]),
    ("skills/help/SKILL.md", r"Same flow, one step at a time", None, list(RANK)),
    ("skills/developer/SKILL.md", r"^\s*\| feature \|", None, ["spec-from-ticket", "clarify", "plan-deep"]),
    ("skills/spec-from-ticket/SKILL.md", r"^Next:\s+/clarify", r"/run-pipeline", ["clarify", "plan-deep"]),
    ("skills/verify/SKILL.md", r"^`/design-recon` \(UI tickets", r"→ `/merge`", ["verify", "review-changes", "pr", "merge"]),
    ("README.md", r"^## The pipeline", r"^## Skills", ["review-changes", "pr", "merge", "bump-submodule"]),
]

def region(lines, start, end):
    for i, l in enumerate(lines):
        if re.search(start, l):
            if end is None:
                return "\n".join(lines[i:i + 1])
            for j in range(i + (1 if end.startswith("^") else 0), len(lines)):
                if re.search(end, lines[j]):
                    return "\n".join(lines[i:j + 1])
            return None
    return None

def problems(text, required):
    seq = []
    # "/pr --implement" is an implement option, not the PR stage
    for n in re.findall(r"/([a-z][a-z0-9-]*)", text.replace("/pr --implement", "")):
        if n in RANK and n not in seq:
            seq.append(n)
    out = [f"missing /{r}" for r in required if r not in seq]
    out += [f"/{b} comes after /{a}" for a, b in zip(seq, seq[1:]) if RANK[a] > RANK[b]]
    return seq, out

def self_test():
    ok = "`/spec-from-ticket` → `/clarify` → `/plan-deep` → `/review-changes` → `/verify` → `/pr` → `/merge`"
    assert problems(ok, ["clarify", "merge"])[1] == []
    assert problems("/plan-deep then /clarify", [])[1] == ["/clarify comes after /plan-deep"]
    assert problems("/spec-from-ticket /pr", ["merge"])[1] == ["missing /merge"]
    print("check-pipeline: self-test ok")

def main():
    if "--self-test" in sys.argv:
        return self_test()
    bad = 0
    for path, start, end, required in CHECKS:
        p = ROOT / path
        text = region(p.read_text().splitlines(), start, end) if p.exists() else None
        if text is None:
            print(f"{path}: cannot find the pipeline text (/{start}/) — update CHECKS in this script"); sys.exit(2)
        seq, out = problems(text, required)
        print(f"{'ok  ' if not out else 'FAIL'} {path}: {' → '.join(seq)}")
        for o in out:
            print(f"       {o}")
        bad += bool(out)
    sys.exit(1 if bad else 0)

main()
