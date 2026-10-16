#!/usr/bin/env python3
"""merge-pr.py — judge ONE Bitbucket `POST .../pullrequests/<id>/merge` response (read from a FILE, never
echoed through a shell) and print a single line on success:

    <repo> #<id> MERGED <full merge commit sha>

exit 0  merged; the line above is on stdout
exit 10 the merge is still running (HTTP 202, or a task-status body that is PENDING) — caller polls again
exit 1  anything else: API error, a state other than MERGED, a body that is not JSON. The verbatim
        error goes to stderr as `ERROR <repo> #<id> HTTP <code>: <message>`.

usage: merge-pr.py <repo> <pr_id> <http_code> <response_file>      |      merge-pr.py --self-test
"""
import json
import sys


def classify(repo, pr_id, code, text):
    """-> (exit_code, stdout_line, stderr_line)"""
    tag = "%s #%s" % (repo, pr_id)
    if str(code) == "202" and not text.strip():  # accepted, the work continues at the Location task URL
        return 10, "", ""
    try:
        body = json.loads(text)
    except ValueError:
        return 1, "", "ERROR %s HTTP %s: response is not JSON: %s" % (tag, code, text[:300].strip())
    if not isinstance(body, dict):
        return 1, "", "ERROR %s HTTP %s: unexpected response: %s" % (tag, code, text[:300].strip())
    if "task_status" in body:  # async merge: GET <Location> answers with a task, the PR sits in merge_result
        status = body.get("task_status")
        if status == "PENDING":
            return 10, "", ""
        if status != "SUCCESS":
            return 1, "", "ERROR %s HTTP %s: merge task %s" % (tag, code, status)
        body = body.get("merge_result") or {}
    elif str(code) == "202":
        return 10, "", ""
    err = body.get("error")
    if err or not str(code).startswith("2"):
        msg = (err or {}).get("message") or text[:300].strip()
        detail = (err or {}).get("detail")
        return 1, "", "ERROR %s HTTP %s: %s%s" % (tag, code, msg, " — %s" % detail if detail else "")
    state = body.get("state")
    sha = (body.get("merge_commit") or {}).get("hash") or ""
    if state != "MERGED" or not sha:
        return 1, "", "ERROR %s HTTP %s: state %s, merge commit %s" % (tag, code, state, sha or "missing")
    return 0, "%s #%s MERGED %s" % (repo, pr_id, sha), ""


def self_test():
    sha = "a" * 40
    cases = [
        ("merged", 200, json.dumps({"state": "MERGED", "merge_commit": {"hash": sha}}), 0),
        ("still open", 200, json.dumps({"state": "OPEN", "merge_commit": None}), 1),
        ("rejected", 409, json.dumps({"error": {"message": "Not approved", "detail": "needs 1 approval"}}), 1),
        # the AR-573 case: JSON escapes that a zsh `echo` turns into real control characters
        ("escaped newline in message", 400, json.dumps({"error": {"message": "line1\nline2 \"quoted\""}}), 1),
        ("not json", 502, "<html>Bad gateway</html>", 1),
        ("async accepted", 202, "", 10),
        ("task pending", 200, json.dumps({"task_status": "PENDING"}), 10),
        ("task done", 200, json.dumps({"task_status": "SUCCESS",
                                       "merge_result": {"state": "MERGED", "merge_commit": {"hash": sha}}}), 0),
        ("task failed", 200, json.dumps({"task_status": "FAILED"}), 1),
    ]
    bad = 0
    for name, code, text, want in cases:
        got, out, _ = classify("be", 7, code, text)
        ok = got == want and (want != 0 or out == "be #7 MERGED " + sha)
        print("%s %s" % ("ok  " if ok else "FAIL", name))
        bad += not ok
    sys.exit(1 if bad else 0)


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    if len(sys.argv) != 5:
        print(__doc__, file=sys.stderr)
        sys.exit(4)
    repo, pr_id, code, path = sys.argv[1:]
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    rc, out, err = classify(repo, pr_id, code, text)
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    sys.exit(rc)


main()
