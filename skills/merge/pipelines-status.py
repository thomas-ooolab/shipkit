#!/usr/bin/env python3
"""pipelines-status.py — pick the pipeline run for ONE merge commit out of `twg bitbucket pipeline
query -o json` output (stdin) and print a single line:

    <repo>|<run#>|<sha8>|<STATE>|<RESULT>

STATE  = PENDING | IN_PROGRESS | COMPLETED | NOTFOUND (no run has that merge commit yet)
RESULT = SUCCESSFUL | FAILED | STOPPED | ERROR | - (PASSED is normalised to SUCCESSFUL)

Matches on target.commit.hash (first 8 chars) == merge sha, never "the most recent run".
usage: pipelines-status.py <repo> <merge_sha> < twg.json      |      pipelines-status.py --self-test
"""
import json
import sys


def find_runs(node):
    """Yield every dict that looks like a pipeline run, wherever twg nests it."""
    if isinstance(node, dict):
        if "target" in node and "state" in node:
            yield node
            return
        for v in node.values():
            yield from find_runs(v)
    elif isinstance(node, list):
        for v in node:
            yield from find_runs(v)


def classify(payload, repo, merge_sha):
    want = merge_sha[:8]
    for run in find_runs(payload):
        commit = ((run.get("target") or {}).get("commit") or {}).get("hash") or ""
        if commit[:8] != want:
            continue
        state = run.get("state") or {}
        st = state.get("name") or "UNKNOWN"
        result = (state.get("result") or {}).get("name") or "-"
        if result == "PASSED":
            result = "SUCCESSFUL"
        num = run.get("build_number") or run.get("number") or run.get("id") or "?"
        return "%s|%s|%s|%s|%s" % (repo, num, want, st, result)
    return "%s|-|%s|NOTFOUND|-" % (repo, want)


def self_test():
    sample = {"values": [
        {"build_number": 12, "target": {"commit": {"hash": "bbbbbbbb11112222"}},
         "state": {"name": "COMPLETED", "result": {"name": "SUCCESSFUL"}}},
        {"build_number": 11, "target": {"commit": {"hash": "aaaaaaaa33334444"}},
         "state": {"name": "COMPLETED", "result": {"name": "FAILED"}}},
        {"build_number": 13, "target": {"commit": {"hash": "cccccccc55556666"}},
         "state": {"name": "IN_PROGRESS"}},
    ]}
    cases = [
        ("be", "aaaaaaaa33334444ffff", "be|11|aaaaaaaa|COMPLETED|FAILED"),      # older run, matched by sha
        ("fe", "bbbbbbbb11112222", "fe|12|bbbbbbbb|COMPLETED|SUCCESSFUL"),
        ("fe", "cccccccc55556666", "fe|13|cccccccc|IN_PROGRESS|-"),
        ("fe", "dddddddd00000000", "fe|-|dddddddd|NOTFOUND|-"),                 # not triggered yet
    ]
    bad = 0
    for repo, sha, want in cases:
        got = classify(sample, repo, sha)
        ok = got == want
        bad += not ok
        print("%s  %s -> %s" % ("PASS" if ok else "FAIL", sha[:8], got))
    print("%d/%d passed" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    if len(sys.argv) != 3:
        sys.exit("usage: pipelines-status.py <repo> <merge_sha> < twg.json  |  --self-test")
    try:
        data = json.load(sys.stdin)
    except ValueError as e:
        print("PARSE_ERROR: %s" % e, file=sys.stderr)
        sys.exit(1)
    print(classify(data, sys.argv[1], sys.argv[2]))
