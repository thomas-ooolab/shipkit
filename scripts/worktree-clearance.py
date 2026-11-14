#!/usr/bin/env python3
"""worktree-clearance.py — read what removing a worktree would lose, and issue the clearance that hooks/worktree-delete-guard.py asks for.

  python3 -I scripts/worktree-clearance.py check <worktree-path>                 # JSON facts, read-only
  python3 -I scripts/worktree-clearance.py grant <worktree-path>                 # clearance, only when git holds nothing to lose
  python3 -I scripts/worktree-clearance.py grant <worktree-path> --user-approved # clearance after the USER said "delete" with the loss in view
  python3 -I scripts/worktree-clearance.py valid <worktree-path>                 # exit 0 when a fresh clearance exists
  python3 -I scripts/worktree-clearance.py --self-test

`check` prints one JSON object: the repos (the worktree root and each initialized submodule) with `branch`, `dirty` (a tree with changes outside `.shipkit/`)
and `unpushed` (commits on no remote), `git_changes` (any repo dirty or ahead), and `shipkit` (each `.shipkit/pipeline-*.md` with its `Status:` line, and the
other state files present) — what `.shipkit/` holds is gitignored and goes with the worktree. Whether the ticket is *in progress* is NOT decided here: the
caller has the Haiku agent `worktree-checker` read those files.
`grant` refuses (exit 3) while `git_changes` is true unless `--user-approved` is given; the clearance lasts 30 minutes and names the path. It never removes anything.
Clearances live in `$SHIPKIT_CLEARANCE_DIR`, default `~/.claude/shipkit/worktree-clearance/`.
Exit: 0 ok · 2 usage or no such worktree · 3 refused (git changes, no --user-approved) · 4 no fresh clearance (valid).
"""
import hashlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path

TTL = 30 * 60


def clearance_dir():
    return Path(os.environ.get("SHIPKIT_CLEARANCE_DIR") or Path.home() / ".claude" / "shipkit" / "worktree-clearance")


def key(path):
    return hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:16]


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def repo_facts(path):
    rc, branch = git(["symbolic-ref", "--short", "-q", "HEAD"], path)
    _, dirty = git(["status", "--porcelain", "--", ".", ":!.shipkit"], path)
    rc_up, ahead = git(["rev-list", "--count", "@{upstream}..HEAD"], path)
    if rc_up != 0:  # no upstream (or detached): commits that sit on no remote at all
        _, ahead = git(["rev-list", "--count", "HEAD", "--not", "--remotes"], path)
    return {"path": str(path), "branch": branch if rc == 0 else "(detached)", "dirty": bool(dirty), "unpushed": int(ahead or 0)}


def facts(worktree):
    wt = Path(worktree).resolve()
    repos = [repo_facts(wt)]
    _, sub = git(["submodule", "status"], wt)
    for line in sub.splitlines():
        if line and line[0] != "-":  # '-' = not initialized, nothing there to lose
            parts = line[1:].split()
            if len(parts) >= 2 and (wt / parts[1] / ".git").exists():
                repos.append(repo_facts(wt / parts[1]))
    ship = wt / ".shipkit"
    pipelines, others = [], []
    if ship.is_dir():
        for f in sorted(ship.glob("pipeline-*.md")):
            status = next((l for l in f.read_text(errors="replace").splitlines() if l.startswith("Status:")), "Status: (none)")
            pipelines.append({"file": f.name, "status": status})
        others = sorted(f.name for f in ship.iterdir() if f.name.split("-")[0] in ("bugfix", "pr", "assign", "clarify", "merge", "evidence"))
    return {"path": str(wt), "repos": repos, "git_changes": any(r["dirty"] or r["unpushed"] for r in repos),
            "shipkit": {"exists": ship.is_dir(), "pipelines": pipelines, "other_state_files": others}}


def valid(worktree, now=None):
    f = clearance_dir() / key(worktree)
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return False
    return (now or time.time()) - d.get("granted_at", 0) < TTL and d.get("path") == str(Path(worktree).resolve())


def grant(worktree, user_approved):
    fa = facts(worktree)
    if fa["git_changes"] and not user_approved:
        print("refused: git holds changes that would be lost (dirty tree or commits on no remote) — ask the user; only an explicit \"delete\" from them "
              "allows `grant --user-approved`", file=sys.stderr)
        return 3
    d = clearance_dir()
    d.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".c-")
    with os.fdopen(fd, "w") as f:
        json.dump({"path": fa["path"], "granted_at": time.time(), "user_approved": bool(user_approved)}, f)
    os.replace(tmp, d / key(worktree))
    print(f"cleared {fa['path']} for {TTL // 60} minutes" + (" (user approved)" if user_approved else ""))
    return 0


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "grant", "valid"):
        print("usage: worktree-clearance.py check|grant|valid <worktree-path> [--user-approved] (try --help)", file=sys.stderr)
        return 2
    cmd, path = argv[0], argv[1]
    if not Path(path).is_dir():
        print(f"no such worktree: {path}", file=sys.stderr)
        return 2
    if cmd == "check":
        print(json.dumps(facts(path), indent=2))
        return 0
    if cmd == "valid":
        return 0 if valid(path) else 4
    return grant(path, "--user-approved" in argv[2:])


def self_test():
    for k in [k for k in os.environ if k.startswith("GIT_")]:  # a pre-commit hook sets GIT_*; the scratch repos must not inherit them
        del os.environ[k]
    base = Path(tempfile.mkdtemp())
    try:
        os.environ["SHIPKIT_CLEARANCE_DIR"] = str(base / "clr")
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", **os.environ}
        run = lambda *a, cwd: subprocess.run(["git", *a], cwd=cwd, env=env, check=True, capture_output=True)
        origin, main_repo, wt = base / "origin.git", base / "main", base / "wt"
        run("init", "-q", "--bare", str(origin), cwd=base)
        run("init", "-q", "-b", "main", str(main_repo), cwd=base)
        run("commit", "-q", "--allow-empty", "-m", "i", cwd=main_repo)
        run("remote", "add", "origin", str(origin), cwd=main_repo)
        run("push", "-q", "origin", "main", cwd=main_repo)
        run("worktree", "add", "-q", "-b", "feat/X-1-a", str(wt), cwd=main_repo)
        run("push", "-q", "-u", "origin", "feat/X-1-a", cwd=wt)
        (wt / ".shipkit").mkdir()
        (wt / ".shipkit" / "pipeline-X-1.md").write_text("# s\nStatus: running · verify\n")
        (wt / ".shipkit" / "bugfix-X-1.md").write_text("x")
        # clean and pushed: no git changes, the state is listed
        fa = facts(wt)
        assert not fa["git_changes"] and fa["shipkit"]["pipelines"][0]["status"].startswith("Status: running") and "bugfix-X-1.md" in fa["shipkit"]["other_state_files"]
        assert not valid(wt) and main(["grant", str(wt)]) == 0 and valid(wt) and main(["valid", str(wt)]) == 0
        assert not valid(wt, now=time.time() + TTL + 5)                      # expires
        # a change under .shipkit alone is not a git change; a real untracked file is
        (wt / ".shipkit" / "x.md").write_text("y")
        assert not facts(wt)["git_changes"]
        (wt / "new.txt").write_text("z")
        assert facts(wt)["git_changes"] and facts(wt)["repos"][0]["dirty"]
        (base / "clr" / key(wt)).unlink()
        assert main(["grant", str(wt)]) == 3 and not valid(wt)               # refused without the user
        assert main(["grant", str(wt), "--user-approved"]) == 0 and valid(wt)
        (wt / "new.txt").unlink()
        # a commit on no remote is a git change
        (wt / "f.txt").write_text("1"); run("add", "f.txt", cwd=wt); run("commit", "-q", "-m", "c", cwd=wt)
        assert facts(wt)["repos"][0]["unpushed"] == 1 and facts(wt)["git_changes"]
        (base / "clr" / key(wt)).unlink()
        assert main(["grant", str(wt)]) == 3
        # usage
        assert main([]) == 2 and main(["check", str(base / "nope")]) == 2 and main(["bogus", str(wt)]) == 2
        print("worktree-clearance self-test: ok")
        return 0
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    if sys.argv[1:] in (["-h"], ["--help"]):
        print(__doc__); sys.exit(0)
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main(sys.argv[1:]))
