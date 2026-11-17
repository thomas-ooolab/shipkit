#!/usr/bin/env python3
"""worktree-clearance.py — read what removing a worktree would lose, and issue the clearance that hooks/worktree-delete-guard.py asks for.

  python3 -I scripts/worktree-clearance.py check <worktree-path>                 # JSON facts, read-only
  python3 -I scripts/worktree-clearance.py grant <worktree-path>                 # clearance, only when git holds nothing to lose
  python3 -I scripts/worktree-clearance.py grant <worktree-path> --user-approved # clearance after the USER said "delete" with the loss in view
  python3 -I scripts/worktree-clearance.py valid <worktree-path>                 # exit 0 when a fresh clearance exists
  python3 -I scripts/worktree-clearance.py prepare <worktree-path>               # a worktree with initialized submodules, made removable WITHOUT --force
  python3 -I scripts/worktree-clearance.py --self-test

`check` prints one JSON object: the repos (the worktree root and each initialized submodule) with `branch`, `dirty` (a tree with changes outside `.shipkit/`)
and `unpushed` (commits on no remote), `git_changes` (any repo dirty or ahead), and `shipkit` (each `.shipkit/pipeline-*.md` with its `Status:` line, and the
other state files present) — what `.shipkit/` holds is gitignored and goes with the worktree. Whether the ticket is *in progress* is NOT decided here: the
caller has the Haiku agent `worktree-checker` read those files.
`grant` refuses (exit 3) while `git_changes` is true unless `--user-approved` is given; the clearance lasts 30 minutes and names the path. `grant` removes nothing.
`prepare` (needs a fresh clearance) is for a linked worktree that has a submodule repository — populated (a gitlink whose directory holds a `.git`, registered or
not: `git submodule status` prints '-' for one never registered) or left in `modules/` by an earlier deinit: Git refuses to remove it without --force because each submodule's
repository sits in the worktree's own git directory (`<primary>/.git/worktrees/<name>/modules/`) and would go with it. Only when every submodule holds nothing
(no uncommitted or untracked change, no stash, no local branch or detached HEAD with commits on no remote) it runs `git submodule deinit --all` (never -f) and deletes
that `modules` directory; then `git worktree remove` / `orca worktree rm` works without --force. Anything held → exit 3, each line on stderr, nothing deleted (it has no
override: the user commits, pushes or discards it). A worktree with no submodule repository → exit 0, nothing to do. `check` lists the same repositories. A primary checkout → exit 2, untouched.
Clearances live in `$SHIPKIT_CLEARANCE_DIR`, default `~/.claude/shipkit/worktree-clearance/`.
Exit: 0 ok · 2 usage, no such worktree or (prepare) not a linked worktree · 3 refused (git changes, no --user-approved; prepare: a submodule holds something) · 4 no fresh clearance (valid, prepare).
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time
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


def submodule_paths(wt):
    """Every submodule that has a repository in the worktree: a gitlink of the index whose directory holds a `.git`. Not `git submodule status`:
    it prints '-' for a submodule that is populated but not registered in the config (no `submodule.<name>.url` / `.active`), and Git refuses
    to remove such a worktree all the same."""
    out = []
    for line in git(["ls-files", "--stage"], wt)[1].splitlines():
        if line.startswith("160000 ") and "\t" in line:
            p = line.split("\t", 1)[1]
            if (wt / p / ".git").exists():
                out.append(wt / p)
    return out


def facts(worktree):
    wt = Path(worktree).resolve()
    repos = [repo_facts(wt)] + [repo_facts(p) for p in submodule_paths(wt)]
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


def submodule_losses(path, gitdir=None):
    """What deleting a submodule's repository would lose: an uncommitted or untracked change, a stash, a local branch or a detached HEAD with
    commits that sit on no remote. [] = nothing. `gitdir` = a repository with no work directory (one left in `modules/`): no tree to look at."""
    g = (lambda a: git(["--git-dir", str(gitdir)] + a, ".")) if gitdir else (lambda a: git(a, path))
    why = []
    if not gitdir and g(["status", "--porcelain"])[1]:
        why.append("uncommitted or untracked changes")
    stash = g(["stash", "list"])[1]
    if stash:
        why.append(f"{len(stash.splitlines())} stash entr{'y' if len(stash.splitlines()) == 1 else 'ies'}")
    for b in g(["for-each-ref", "--format=%(refname:short)", "refs/heads"])[1].splitlines():
        n = int(g(["rev-list", "--count", b, "--not", "--remotes"])[1] or 0)
        if n:
            why.append(f"branch {b}: {n} commit(s) on no remote")
    if g(["symbolic-ref", "-q", "HEAD"])[0] != 0:  # detached
        n = int(g(["rev-list", "--count", "HEAD", "--not", "--remotes"])[1] or 0)
        if n:
            why.append(f"detached HEAD: {n} commit(s) on no remote")
    return why


def prepare(worktree):
    """Make a linked worktree with initialized submodules removable by git WITHOUT --force. Git refuses to remove it because each submodule's
    repository lives in <primary>/.git/worktrees/<name>/modules/, i.e. inside the worktree's own git directory; deleting the worktree deletes that
    repository, so it is deleted here only when it holds nothing: every submodule has no uncommitted or untracked change, no stash, and no local
    branch or detached HEAD with commits on no remote. Then `git submodule deinit --all` (never -f) and the `modules` directory goes."""
    wt = Path(worktree).resolve()
    if not valid(wt):
        print("no fresh clearance: run `grant` first", file=sys.stderr)
        return 4
    gd = git(["rev-parse", "--absolute-git-dir"], wt)[1]
    common = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], wt)[1]
    if not gd or not common or Path(gd).resolve().parent != (Path(common) / "worktrees").resolve():
        print(f"not a linked worktree: {wt} (its git directory is not <primary>/.git/worktrees/<name>); nothing touched", file=sys.stderr)
        return 2
    subs = submodule_paths(wt)
    mods = Path(gd).resolve() / "modules"
    own = {Path(git(["rev-parse", "--absolute-git-dir"], p)[1]).resolve() for p in subs}
    # a repository in modules/ that no work directory points at (a submodule deinitialized earlier): Git refuses to remove the worktree for it too
    orphans = sorted(d for d in mods.iterdir() if d.is_dir() and d.resolve() not in own) if mods.is_dir() else []
    if not subs and not orphans:
        print("no submodule repository: nothing to prepare")
        return 0
    lost = [(str(p.relative_to(wt)), w) for p in subs for w in submodule_losses(p)]
    lost += [(f"modules/{d.name} (no work directory)", w) for d in orphans for w in submodule_losses(None, d)]
    if lost:
        for label, w in lost:
            print(f"submodule {label}: {w}", file=sys.stderr)
        print("kept: removing the worktree would lose the above; nothing deleted", file=sys.stderr)
        return 3
    # `git submodule status` shows '-' for a populated submodule that was never registered, and deinit only clears registered ones: register first
    rel = [str(p.relative_to(wt)) for p in subs]
    if rel:
        subprocess.run(["git", "submodule", "init", "--", *rel], cwd=wt, capture_output=True, text=True)
    r = subprocess.run(["git", "submodule", "deinit", "--all"], cwd=wt, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"git submodule deinit refused (not forced): {r.stderr.strip() or r.stdout.strip()}", file=sys.stderr)
        return 3
    left = [p for p in subs if (p / ".git").exists()]
    if left:
        print(f"git submodule deinit left {', '.join(str(p.relative_to(wt)) for p in left)} populated; nothing deleted", file=sys.stderr)
        return 3
    if mods.is_dir():
        shutil.rmtree(mods)
    print(f"prepared {wt}: {len(subs)} submodule(s) deinitialized and their repositories ({mods}) removed; `git worktree remove` needs no --force now")
    return 0


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "grant", "valid", "prepare"):
        print("usage: worktree-clearance.py check|grant|valid|prepare <worktree-path> [--user-approved] (try --help)", file=sys.stderr)
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
    if cmd == "prepare":
        return prepare(path)
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
        # --- prepare: a worktree with an initialized submodule becomes removable by git without --force, only when nothing in it would be lost
        sub_src = base / "subsrc"
        run("init", "-q", "-b", "main", str(sub_src), cwd=base); run("commit", "-q", "--allow-empty", "-m", "s", cwd=sub_src)
        P = ("-c", "protocol.file.allow=always")

        def mk(name):
            prim, w = base / f"p-{name}", base / f"w-{name}"
            run("init", "-q", "-b", "main", str(prim), cwd=base)
            run(*P, "submodule", "add", "-q", str(sub_src), "sub", cwd=prim); run("commit", "-q", "-m", "a", cwd=prim)
            run("worktree", "add", "-q", "-b", "w", str(w), cwd=prim)
            run(*P, "submodule", "update", "-q", "--init", cwd=w)
            return prim, w, w / "sub"

        def mods(w):
            return Path(subprocess.run(["git", "rev-parse", "--absolute-git-dir"], cwd=w, capture_output=True, text=True).stdout.strip()) / "modules"

        prim, w, sub = mk("clean")
        assert main(["prepare", str(w)]) == 4 and mods(w).is_dir()                                # no clearance: nothing touched
        assert subprocess.run(["git", "worktree", "remove", str(w)], cwd=prim, capture_output=True).returncode != 0   # git refuses, as the bug says
        assert main(["grant", str(w), "--user-approved"]) == 0 and main(["prepare", str(w)]) == 0
        assert not mods(w).exists() and not (sub / ".git").exists()
        run("worktree", "remove", str(w), cwd=prim)                                               # no --force: check=True would raise
        assert not w.exists()
        for name, setup, what in (
            ("dirty", lambda s: (s / "u.txt").write_text("x"), "uncommitted or untracked"),
            ("head", lambda s: (run("checkout", "-q", "-b", "feat", cwd=s), run("commit", "-q", "--allow-empty", "-m", "c", cwd=s)), "branch feat: 1 commit"),
            ("branch", lambda s: (run("checkout", "-q", "-b", "old", cwd=s), run("commit", "-q", "--allow-empty", "-m", "c", cwd=s), run("checkout", "-q", "--detach", "origin/main", cwd=s)), "branch old: 1 commit"),
            ("stash", lambda s: ((s / "u.txt").write_text("x"), run("stash", "-q", "-u", cwd=s)), "stash entry"),
        ):
            prim, w, sub = mk(name)
            setup(sub)
            assert main(["grant", str(w), "--user-approved"]) == 0
            assert main(["prepare", str(w)]) == 3 and mods(w).is_dir() and (sub / ".git").exists(), name   # held: nothing deleted
            assert what in "; ".join(submodule_losses(sub)), (name, submodule_losses(sub))
        def unregister(prim):   # what real worktrees looked like: populated, no submodule.<name>.url / .active anywhere, `submodule status` prints '-'
            for k in ("url", "active"):
                subprocess.run(["git", "config", "--unset", f"submodule.sub.{k}"], cwd=prim, env=env)
        prim, w, sub = mk("unreg")
        unregister(prim)
        assert git(["submodule", "status"], w)[1].startswith("-") and (sub / ".git").exists()
        assert len(facts(w)["repos"]) == 2                                                        # check() sees it although status says '-'
        assert main(["grant", str(w), "--user-approved"]) == 0 and main(["prepare", str(w)]) == 0
        run("worktree", "remove", str(w), cwd=prim)
        assert not w.exists()
        prim, w, sub = mk("unreg-dirty")
        unregister(prim)
        (sub / "u.txt").write_text("x")
        assert facts(w)["repos"][1]["dirty"] and main(["grant", str(w), "--user-approved"]) == 0
        assert main(["prepare", str(w)]) == 3 and mods(w).is_dir() and (sub / ".git").exists()
        prim, w, sub = mk("orphan")                                                               # deinitialized earlier: the repository stays in modules/
        run("submodule", "deinit", "--all", cwd=w)
        assert not (sub / ".git").exists() and mods(w).is_dir()
        assert main(["grant", str(w), "--user-approved"]) == 0 and main(["prepare", str(w)]) == 0
        run("worktree", "remove", str(w), cwd=prim)
        assert not w.exists()
        prim, w, sub = mk("orphan-held")
        run("checkout", "-q", "-b", "old", cwd=sub); run("commit", "-q", "--allow-empty", "-m", "c", cwd=sub); run("checkout", "-q", "--detach", "origin/main", cwd=sub)
        run("submodule", "deinit", "--all", cwd=w)
        assert main(["grant", str(w), "--user-approved"]) == 0 and main(["prepare", str(w)]) == 3 and mods(w).is_dir()
        assert main(["grant", str(wt), "--user-approved"]) == 0 and main(["prepare", str(wt)]) == 0 and wt.exists()   # no submodule: nothing to do
        assert main(["grant", str(main_repo), "--user-approved"]) == 0 and main(["prepare", str(main_repo)]) == 2     # a primary checkout is never touched
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
