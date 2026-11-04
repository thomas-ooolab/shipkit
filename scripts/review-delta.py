#!/usr/bin/env python3
"""Measure the delta of each review target since its last reviewed sha, for /pr's full-review gate (review-loop Step 6).

usage: python3 -I scripts/review-delta.py [--config skills/pr/config.json] PATH:REVIEWED:HEAD [...]
       REVIEWED is `-` when the bot never named a sha (→ full review).
       python3 -I scripts/review-delta.py --self-test

Prints JSON: per target the line counts by kind, the sensitive paths it touches, and the reasons it needs a full review
by size or path. It does not read the verdict: P1/P2 labels, the 4b severity stop and the round cap stay with the loop.
Line kinds: test (test files), docs (*.md, docs/), generated (*.gen.go, *.pb.go, ...; not code when no contract file is
in the delta), comment (a code line that is only a comment or blank), code (everything else; a line that cannot be placed
counts as code).
"""
import json
import os
import re
import subprocess
import sys

TEST_RE = re.compile(r"(^|/)(__tests__|tests?)/|_test\.go$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$|(^|/)test_[^/]*\.py$|_test\.py$")
DOCS_RE = re.compile(r"(^|/)docs/|\.md$")
GEN_RE = re.compile(r"\.gen\.go$|_gen\.go$|\.pb\.go$|\.generated\.")
CONTRACT_RE = re.compile(r"\.proto$|(^|/)api\.ya?ml$|openapi[^/]*$|swagger[^/]*$")
COMMENT_PREFIXES = ("//", "#", "/*", "*", "--", "<!--")
DEFAULT_CONFIG = "skills/pr/config.json"


def glob_to_regex(pat):
    out, i = "", 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out, i = out + "(.*/)?", i + 3
        elif pat.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pat[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pat[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pat[i]), i + 1
    return re.compile("^" + out + "$")


def git(path, *args):
    return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, check=True).stdout


def measure(path, reviewed, head, sensitive, limits):
    """Measurement for one target. reviewed == '-' means no reviewed sha is known."""
    if reviewed == "-":
        return {"repo": path, "reviewed": None, "head": head, "full_review_reasons": ["no reviewed sha"]}
    files = {}
    for line in git(path, "diff", "--numstat", "-M", f"{reviewed}..{head}").splitlines():
        adds, dels, name = line.split("\t", 2)
        files[name] = {"added": 0 if adds == "-" else int(adds), "deleted": 0 if dels == "-" else int(dels)}
    contract_in_delta = any(CONTRACT_RE.search(f) for f in files)

    kind_of = {}
    for name in files:
        if TEST_RE.search(name):
            kind_of[name] = "test"
        elif DOCS_RE.search(name):
            kind_of[name] = "docs"
        elif GEN_RE.search(name) and not contract_in_delta:
            kind_of[name] = "generated"
        else:
            kind_of[name] = "code"

    counts = {"code": 0, "comment": 0, "test": 0, "docs": 0, "generated": 0}
    current = None
    for line in git(path, "diff", "-U0", "-M", f"{reviewed}..{head}").splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            continue
        if line.startswith("--- ") or line.startswith("diff ") or current is None:
            continue
        if not line or line[0] not in "+-":
            continue
        kind = kind_of.get(current, "code")
        text = line[1:].strip()
        if kind == "code" and (not text or text.startswith(COMMENT_PREFIXES)):
            counts["comment"] += 1
        else:
            counts[kind] += 1

    delta_total = sum(f["added"] + f["deleted"] for f in files.values())
    hits = sorted(f for f in files if any(p.match(f) for p in sensitive))
    reasons = []
    if hits:
        reasons.append(f"touches sensitive path: {', '.join(hits)}")
    if counts["code"] > limits["max_unreviewed_code_lines"]:
        reasons.append(f"code lines {counts['code']} > {limits['max_unreviewed_code_lines']}")
    if delta_total > limits["max_unreviewed_delta_lines"]:
        reasons.append(f"delta lines {delta_total} > {limits['max_unreviewed_delta_lines']}")
    return {
        "repo": path, "reviewed": reviewed, "head": head, "files": len(files),
        "code_lines": counts["code"], "comment_lines": counts["comment"], "test_lines": counts["test"],
        "docs_lines": counts["docs"], "generated_lines": counts["generated"], "delta_lines": delta_total,
        "sensitive_hits": hits, "full_review_reasons": reasons,
    }


def load_limits(config):
    with open(config, encoding="utf-8") as f:
        review = json.load(f)["review"]
    limits = {"max_unreviewed_code_lines": review["max_unreviewed_code_lines"],
              "max_unreviewed_delta_lines": review["max_unreviewed_delta_lines"]}
    return limits, [glob_to_regex(p) for p in review["sensitive_paths"]]


def self_test():
    import tempfile
    repo = os.path.join(tempfile.mkdtemp(prefix="review-delta-"), "r")
    os.makedirs(repo)
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def git_run(*args):
        subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, env=env)

    def write(name, text):
        full = os.path.join(repo, name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)

    def commit(msg):
        git_run("add", "-A")
        git_run("commit", "-q", "-m", msg)
        return git(repo, "rev-parse", "HEAD").strip()

    git_run("init", "-q")
    write("app.go", "package app\n\nfunc a() int {\n\treturn 1\n}\n")
    write("app_test.go", "package app\n")
    write("notes.md", "old\n")
    base = commit("base")

    # app.go: -return 1 (code), +// comment (comment), +return 2 (code), +func b (code) → code 3, comment 1
    # app_test.go: +blank, +func TestA (test) → test 2 ; notes.md: -old +new (docs) → docs 2
    write("app.go", "package app\n\n// a returns one\nfunc a() int {\n\treturn 2\n}\nfunc b() int { return 3 }\n")
    write("app_test.go", "package app\n\nfunc TestA() {}\n")
    write("notes.md", "new\n")
    head = commit("change")

    limits = {"max_unreviewed_code_lines": 30, "max_unreviewed_delta_lines": 200}
    sensitive = [glob_to_regex(p) for p in ["**/migrations/**", "**/auth/**"]]
    m = measure(repo, base, head, sensitive, limits)
    assert (m["code_lines"], m["comment_lines"], m["test_lines"], m["docs_lines"]) == (3, 1, 2, 2), m
    assert m["sensitive_hits"] == [] and m["full_review_reasons"] == [], m

    # a migration touches a sensitive path → full review, whatever the size
    write("db/migrations/001.sql", "create table x();\n")
    head2 = commit("migration")
    m2 = measure(repo, head, head2, sensitive, limits)
    assert m2["sensitive_hits"] == ["db/migrations/001.sql"], m2
    assert any(r.startswith("touches sensitive path") for r in m2["full_review_reasons"]), m2

    # the same change against a zero code limit → size reason as well
    tight = measure(repo, head, head2, sensitive, {"max_unreviewed_code_lines": 0, "max_unreviewed_delta_lines": 200})
    assert any(r.startswith("code lines") for r in tight["full_review_reasons"]), tight

    # no reviewed sha → full review
    none = measure(repo, "-", head, sensitive, limits)
    assert none["full_review_reasons"] == ["no reviewed sha"], none
    print("ok    review-delta self-test")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    config = DEFAULT_CONFIG
    args = list(argv)
    if "--config" in args:
        i = args.index("--config")
        config = args[i + 1]
        del args[i:i + 2]
    limits, sensitive = load_limits(config)
    targets = []
    for spec in args:
        path, reviewed, head = spec.rsplit(":", 2)
        targets.append(measure(path, reviewed, head, sensitive, limits))
    print(json.dumps({"targets": targets,
                      "full_review": any(t["full_review_reasons"] for t in targets)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
