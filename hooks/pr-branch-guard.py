#!/usr/bin/env python3
"""PreToolUse hook: on Saturday and Sunday, `git push` to a branch that already has an open pull request is blocked — commit only.

Why: a push to a PR branch notifies the people on that PR (Slack, e-mail), which must not happen at the weekend. Committing
locally stays allowed, and so does any push on a weekday — the hook does not even query the host then.
How: for each `git push` in a Bash command it works out the branch(es) being pushed (explicit refspec, `HEAD`, or the
current branch; `--all` / `--mirror` mean every local branch), asks the remote's host which branches have an open PR
(Bitbucket: scripts/bitbucket-api.sh with BITBUCKET_USERNAME / BITBUCKET_APP_PASSWORD, an API token works; GitHub: `gh`),
and blocks when one of them does. A push of a branch with no open PR passes. If the host cannot be asked (no credentials,
network, unknown host) the push is blocked too — "unknown" is not "no PR"; fix the cause or lift the guard.

Not covered: pushes through an MCP tool, and anything the user types in their own terminal.
The day is the machine's local day (SHIPKIT_TZ=<IANA zone> to use another). SHIPKIT_ALLOW_WEEKEND=1, set before Claude Code starts
(an inline `VAR=1 cmd` does not count), lifts the guard for the session — the same switch as weekend-guard.py.

stdin: the hook JSON (tool_name, tool_input, cwd). Exit 0 = allow; exit 2 = block, the reason on stderr goes to the model.
Usage: python3 -I pr-branch-guard.py [--self-test]
"""
import importlib.util, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("common", os.path.join(HERE, "common.py"))
common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common)

PUSH_FLAGS_WITH_VALUE = {"--repo", "--receive-pack", "--exec", "-o", "--push-option", "--force-with-lease-x"}
GLOBAL_FLAGS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

def parse_push(words):
    """words of one `git …` segment -> None if it is not a push, else
    {"dir": <-C dir or None>, "remote": str|None, "refspecs": [...], "all": bool, "delete": bool, "tags_only": bool}"""
    i, d = 1, None
    while i < len(words) and words[i].startswith("-"):
        w = words[i]
        if w == "-C" and i + 1 < len(words):
            d = words[i + 1]
        i += 2 if w in GLOBAL_FLAGS_WITH_VALUE else 1
    if i >= len(words) or words[i] != "push":
        return None
    args, pos, flags = words[i + 1:], [], set()
    j = 0
    while j < len(args):
        a = args[j]
        if a == "--":
            pos += args[j + 1:]; break
        if a.startswith("-"):
            flags.add(a.split("=", 1)[0])
            if a in PUSH_FLAGS_WITH_VALUE:
                j += 1
        else:
            pos.append(a)
        j += 1
    return {"dir": d, "remote": pos[0] if pos else None, "refspecs": pos[1:],
            "all": bool(flags & {"--all", "--mirror"}), "delete": bool(flags & {"-d", "--delete"}),
            "tags_only": "--tags" in flags}

def target_branches(push, git):
    """-> (branches to check, remote name/url). `git(args...)` runs git in the right directory and returns stdout or None."""
    cur = git("symbolic-ref", "--short", "-q", "HEAD")
    remote = push["remote"] or (git("config", f"branch.{cur}.remote") if cur else None) or "origin"
    if push["all"]:
        heads = git("for-each-ref", "--format=%(refname:short)", "refs/heads") or ""
        return [h for h in heads.split() if h], remote
    branches = []
    for spec in push["refspecs"]:
        spec = spec.lstrip("+")
        dst = spec.split(":", 1)[1] if ":" in spec else spec
        if not dst and ":" in spec:               # `src:` — nothing to push to
            continue
        if dst == "HEAD" or (not push["delete"] and ":" not in spec and spec == "HEAD"):
            dst = cur or ""
        dst = re.sub(r"^refs/heads/", "", dst)
        if dst and not dst.startswith("refs/"):   # refs/tags/…, refs/for/… are not branches with PRs
            branches.append(dst)
    if not push["refspecs"] and cur and not push["tags_only"]:   # `git push --tags` sends tags, not the branch
        branches.append(cur)
    return branches, remote

def parse_remote(url):
    """-> (host, 'owner/repo') from git@host:owner/repo.git, https://host/owner/repo.git, ssh://git@host/owner/repo.git."""
    m = re.match(r"^(?:[\w+.-]+://)?(?:[^@/]+@)?([^:/]+)[:/](?:\d+/)?(.+?)(?:\.git)?/?$", url.strip())
    return (m.group(1), m.group(2)) if m else (None, None)

def open_prs(url, env):
    """-> ({branch: '#id'} of open PRs, None) or (None, why it could not be asked)."""
    host, path = parse_remote(url)
    if not host or "/" not in (path or ""):
        return None, f"cannot read the remote URL {url!r}"
    try:
        if "bitbucket" in host:
            helper = os.path.join(HERE, "..", "scripts", "bitbucket-api.sh")
            nxt = f"/repositories/{path}/pullrequests?state=OPEN&pagelen=50&fields=next,values.id,values.source.branch.name"
            found = {}
            for _ in range(10):
                r = subprocess.run(["bash", helper, "GET", nxt], capture_output=True, text=True, timeout=20, env=env)
                if r.returncode != 0:
                    return None, (r.stderr.strip() or f"bitbucket-api.sh exit {r.returncode}")[:200]
                page = json.loads(r.stdout)
                for v in page.get("values", []):
                    found[v["source"]["branch"]["name"]] = f"#{v['id']}"
                nxt = page.get("next")
                if not nxt:
                    return found, None
            return found, None
        if host == "github.com":
            r = subprocess.run(["gh", "pr", "list", "--repo", path, "--state", "open", "--json", "number,headRefName", "--limit", "300"],
                               capture_output=True, text=True, timeout=20, env=env)
            if r.returncode != 0:
                return None, (r.stderr.strip() or f"gh exit {r.returncode}")[:200]
            return {p["headRefName"]: f"#{p['number']}" for p in json.loads(r.stdout)}, None
        return None, f"unknown git host {host!r}"
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as e:
        return None, f"{type(e).__name__}: {e}"[:200]

def make_git(directory):
    def git(*args):
        try:
            r = subprocess.run(["git", "-C", directory, *args], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    return git

def decide(command, cwd, env, now, lookup=open_prs, git_for=make_git):
    """-> None to allow, else the message to show."""
    if env.get("SHIPKIT_ALLOW_WEEKEND") == "1" or not common.is_weekend(now):
        return None
    directory = cwd or os.getcwd()
    for seg, words in common.segments(command, {"git", "cd"} | common.SHELLS):
        if os.path.basename(words[0]) == "cd":
            if len(words) > 1:
                directory = os.path.normpath(os.path.join(directory, os.path.expanduser(words[1])))
            continue
        if os.path.basename(words[0]) != "git":
            continue
        push = parse_push(words)
        if not push:
            continue
        pdir = os.path.normpath(os.path.join(directory, push["dir"])) if push["dir"] else directory
        git = git_for(pdir)
        branches, remote = target_branches(push, git)
        if not branches:
            continue
        url = remote if re.search(r"[:/]", remote) else git("remote", "get-url", "--push", remote)
        if not url:
            return f"shipkit PR-branch guard: blocked at the weekend — cannot tell where `git push {remote}` goes from {pdir}, so cannot check for an open PR."
        prs, why = lookup(url, env)
        if prs is None:
            return (f"shipkit PR-branch guard: blocked at the weekend — could not check whether {', '.join(branches)} has an open pull request ({why}). "
                    "A push is blocked while that is unknown. Commit instead; the user pushes. "
                    "(Fix the credentials, or the user can lift the guard with SHIPKIT_ALLOW_WEEKEND=1 in Claude Code's environment.)")
        hit = [f"{b} (PR {prs[b]})" for b in branches if b in prs]
        if hit:
            return (f"shipkit PR-branch guard: blocked at the weekend — {', '.join(hit)} already has an open pull request. "
                    "Only `git commit` is allowed here: commit locally, do not push, and tell the user it is ready to push. "
                    "(The user can lift the guard with SHIPKIT_ALLOW_WEEKEND=1 in Claude Code's environment.)")
    return None

def self_test():
    P = lambda c: parse_push(common.words_of(c))
    assert P("git push") == {"dir": None, "remote": None, "refspecs": [], "all": False, "delete": False, "tags_only": False}
    assert P("git push -u origin feat/x")["refspecs"] == ["feat/x"]
    assert P("git -C sub -c a=b push --force-with-lease origin HEAD:feat/y")["dir"] == "sub"
    assert P("git push --all")["all"] and P("git push --delete origin old")["delete"]
    assert P("git commit -m 'git push'") is None and P("git status") is None
    assert parse_remote("git@ooolab.bitbucket:ws/repo.git") == ("ooolab.bitbucket", "ws/repo")
    assert parse_remote("https://github.com/o/r.git") == ("github.com", "o/r")
    assert parse_remote("ssh://git@bitbucket.org:7999/ws/repo") == ("bitbucket.org", "ws/repo")

    heads = {"feat/x": 1, "feat/free": 1, "main": 1}
    def git_for(d):
        def git(*a):
            if a[:2] == ("symbolic-ref", "--short"): return "feat/x"
            if a[0] == "config": return None
            if a[:2] == ("remote", "get-url"): return "git@bitbucket.org:ws/repo.git"
            if a[0] == "for-each-ref": return "\n".join(heads)
        return git
    calls = []
    def lookup(url, env):
        calls.append(url)
        return {"feat/x": "#7"}, None
    import datetime
    sat, mon = datetime.datetime(2026, 10, 17, 12), datetime.datetime(2026, 10, 19, 12)
    D = lambda c, env={}, lk=lookup, now=sat: decide(c, "/repo", env, now, lk, git_for)
    blocked = ["git push", "git push origin", "git push -u origin feat/x", "git push origin HEAD", "git push origin feat/free feat/x",
               "git push origin +feat/x", "git push --force-with-lease origin feat/x:feat/x", "git push origin HEAD:refs/heads/feat/x",
               "git push --all", "git push --delete origin feat/x", "git push origin :feat/x", "cd /repo/sub && git push",
               "bash -c 'git push origin feat/x'", "git -C sub push", "git add . && git commit -m x && git push"]
    allowed = ["git commit -am x", "git status", "git push origin feat/free", "git push origin main", "git push --tags",
               "git push origin refs/tags/v1", "git log --oneline", "echo git push", "git commit -m 'git push origin feat/x'",
               "cat <<'EOF'\ngit push\nEOF"]
    for c in blocked:
        m = D(c); assert m and "open pull request" in m, f"should block: {c!r} -> {m}"
        assert D(c, now=datetime.datetime(2026, 10, 18, 9)), f"Sunday too: {c!r}"
    for c in allowed:
        assert D(c) is None, f"should allow: {c!r}"
    assert D("git push", {"SHIPKIT_ALLOW_WEEKEND": "1"}) is None
    n = len(calls)
    for c in blocked:
        assert D(c, now=mon) is None, f"weekday must allow: {c!r}"
    assert len(calls) == n, "a weekday push must not even query the host"
    m = D("git push", lk=lambda u, e: (None, "BITBUCKET_USERNAME not set")); assert m and "could not check" in m and "BITBUCKET_USERNAME" in m
    assert D("git push origin feat/free", lk=lambda u, e: ({}, None)) is None
    assert D("git push git@github.com:o/r.git feat/x") and calls[-1] == "git@github.com:o/r.git"
    # open_prs against a faked subprocess: Bitbucket pagination, GitHub, and the failure paths
    real = subprocess.run
    class R:
        def __init__(s, out="", rc=0, err=""): s.stdout, s.returncode, s.stderr = out, rc, err
    pages = iter([R(json.dumps({"values": [{"id": 1, "source": {"branch": {"name": "a"}}}], "next": "https://api.bitbucket.org/2.0/p2"})),
                  R(json.dumps({"values": [{"id": 2, "source": {"branch": {"name": "b"}}}]}))])
    try:
        subprocess.run = lambda *a, **k: next(pages)
        assert open_prs("git@ooolab.bitbucket:ws/repo.git", {}) == ({"a": "#1", "b": "#2"}, None)
        subprocess.run = lambda *a, **k: R("", 4, "BITBUCKET_USERNAME / BITBUCKET_APP_PASSWORD not set")
        got, why = open_prs("git@bitbucket.org:ws/repo.git", {}); assert got is None and "not set" in why
        subprocess.run = lambda *a, **k: R(json.dumps([{"number": 9, "headRefName": "feat/z"}]))
        assert open_prs("https://github.com/o/r.git", {}) == ({"feat/z": "#9"}, None)
        got, why = open_prs("git@gitlab.example.com:o/r.git", {}); assert got is None and "unknown git host" in why
        subprocess.run = lambda *a, **k: R("not json")
        got, why = open_prs("git@bitbucket.org:ws/repo.git", {}); assert got is None and "JSONDecodeError" in why
    finally:
        subprocess.run = real
    print("pr-branch-guard: self-test ok")

def main():
    if "--self-test" in sys.argv:
        return self_test()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if event.get("tool_name") != "Bash":
        return
    msg = decide((event.get("tool_input") or {}).get("command", ""), event.get("cwd"), os.environ, common.now_in(os.environ))
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
