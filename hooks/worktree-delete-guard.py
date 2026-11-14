#!/usr/bin/env python3
"""PreToolUse hook: removing a git worktree needs a clearance first, in every session — no skill has to be loaded.

Blocked until `scripts/worktree-clearance.py grant <path>` has issued a fresh clearance for that worktree:
  - `orca worktree rm --worktree <selector>` (also `orca-ide`, `orca-dev`) — what /orca-cli runs
  - `git [-C dir] worktree remove <path>`
  - `rm -r…` of a folder that is a registered worktree of the repository the command runs in
The clearance is issued automatically only when git holds nothing to lose; a dirty tree or a commit on no remote needs the user's explicit "delete"
(`grant <path> --user-approved`). Whether the ticket is still in progress is read by the Haiku agent `shipkit:worktree-checker`; the block message says how.
Why: a worktree's `.shipkit/` (ticket state, evidence, drafts) is gitignored and goes with it, Orca drops the local branch, and an unpushed commit survives
only in the reflog.

SHIPKIT_ALLOW_WORKTREE_RM=1, set before Claude Code starts, lifts the block for that session. Not covered: a removal typed in the user's own terminal.
stdin: the hook JSON (tool_name, tool_input, cwd). Exit 0 = allow; exit 2 = block, the reason on stderr goes to the model.
Usage: python3 -I worktree-delete-guard.py [--self-test]
"""
import importlib.util, json, os, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


common = load("common", HERE / "common.py")
clearance = load("worktree_clearance", HERE.parent / "scripts" / "worktree-clearance.py")
SCRIPT = HERE.parent / "scripts" / "worktree-clearance.py"
ORCA = {"orca", "orca-ide", "orca-dev"}
RUNNERS = ORCA | {"git", "rm"} | common.SHELLS


def registered_worktrees(cwd):
    r = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=cwd, capture_output=True, text=True)
    out, cur = [], {}
    for line in r.stdout.splitlines() + [""]:
        if not line:
            if cur:
                out.append(cur)
            cur = {}
        elif " " in line:
            k, v = line.split(" ", 1)
            cur[k] = v
        else:
            cur[line] = True
    return out  # the first entry is the main checkout


def resolve_selector(sel, cwd):
    """An Orca --worktree selector -> an absolute path, or None when it cannot be told."""
    if sel.startswith("id:") and "::" in sel:
        return sel.rsplit("::", 1)[1]
    if sel.startswith("path:"):
        return sel[5:]
    if sel in ("active", "current"):
        return cwd
    name = re.sub(r"^(branch|name|id):", "", sel)
    for wt in registered_worktrees(cwd):
        if Path(wt.get("worktree", "")).name == name or wt.get("branch", "").endswith("/" + name) or wt.get("branch", "") == "refs/heads/" + name:
            return wt["worktree"]
    return None


def targets(command, cwd):
    """-> list of (path or None, what) for every worktree removal the command contains."""
    found = []
    for _seg, words in common.segments(command, RUNNERS):
        exe = os.path.basename(words[0])
        if exe in ORCA and "worktree" in words and "rm" in words[words.index("worktree"):]:
            sel = None
            for i, w in enumerate(words):
                if w == "--worktree" and i + 1 < len(words):
                    sel = words[i + 1]
                elif w.startswith("--worktree="):
                    sel = w.split("=", 1)[1]
            found.append((resolve_selector(sel, cwd) if sel else None, f"`{exe} worktree rm`"))
        elif exe == "git":
            args, c_dir, i = words[1:], cwd, 0
            while i < len(args) and args[i].startswith("-"):
                if args[i] == "-C" and i + 1 < len(args):
                    c_dir = str(Path(c_dir) / args[i + 1]); i += 1
                i += 1
            if args[i:i + 2] == ["worktree", "remove"]:
                rest = [a for a in args[i + 2:] if not a.startswith("-")]
                found.append((str(Path(c_dir) / rest[-1]) if rest else None, "`git worktree remove`"))
        elif exe == "rm" and any(re.match(r"-\w*[rR]", a) for a in words[1:] if a.startswith("-")):
            wts = {str(Path(w["worktree"]).resolve()) for w in registered_worktrees(cwd)[1:]}
            for a in words[1:]:
                if not a.startswith("-") and str((Path(cwd) / a).resolve()) in wts:
                    found.append((str(Path(cwd) / a), "a recursive delete of a registered worktree"))
    return found


def message(path, what):
    where = path or "(which one could not be told — pass it as id:<repoId>::<path>)"
    return (f"shipkit worktree guard: blocked — {what} would remove the worktree {where}. A worktree holds state that lives nowhere else: .shipkit/ is gitignored "
            "(the ticket's stage, evidence, Jira drafts go with it), Orca drops the local branch, and a commit not on origin survives only in the reflog. Nothing was removed.\n"
            f"1. Read the facts: python3 -I {SCRIPT} check <path>\n"
            "2. Dispatch the Haiku agent shipkit:worktree-checker with the path and those facts; it reads <path>/.shipkit and says in_progress or not.\n"
            f"3. Not in progress AND git_changes false → decide alone, no question to the user: python3 -I {SCRIPT} grant <path>, then run the same command again.\n"
            "4. In progress, or ANY git change (a dirty tree or commits on no remote) → do not remove. Ask the user why they want it gone and show what would be lost; "
            f"only after their explicit \"delete\": python3 -I {SCRIPT} grant <path> --user-approved, then run the command again. Never --force.")


def decide(command, cwd, env):
    """-> None to allow, else the message to show."""
    if env.get("SHIPKIT_ALLOW_WORKTREE_RM") == "1":
        return None
    for path, what in targets(command, cwd):
        if path is not None and not Path(path).exists():
            continue  # already gone: nothing left to lose
        if path is None or not clearance.valid(path):
            return message(path, what)
    return None


def self_test():
    for k in [k for k in os.environ if k.startswith("GIT_")]:
        del os.environ[k]
    base = Path(tempfile.mkdtemp())
    try:
        os.environ["SHIPKIT_CLEARANCE_DIR"] = str(base / "clr")
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", **os.environ}
        run = lambda *a, cwd: subprocess.run(["git", *a], cwd=cwd, env=env, check=True, capture_output=True)
        main_repo, wt = base / "main", base / "wt-x"
        run("init", "-q", "-b", "main", str(main_repo), cwd=base)
        run("commit", "-q", "--allow-empty", "-m", "i", cwd=main_repo)
        origin = base / "origin.git"
        run("init", "-q", "--bare", str(origin), cwd=base)
        run("remote", "add", "origin", str(origin), cwd=main_repo)
        run("push", "-q", "origin", "main", cwd=main_repo)
        run("worktree", "add", "-q", "-b", "feat/X-1-a", str(wt), cwd=main_repo)
        run("push", "-q", "-u", "origin", "feat/X-1-a", cwd=wt)
        D = lambda c, cwd=str(main_repo), e={}: decide(c, cwd, e)
        blocked = [
            f"orca worktree rm --worktree id:repo1::{wt} --json",
            f"orca-ide worktree rm --worktree path:{wt}",
            "orca worktree rm --worktree wt-x --json",
            "orca worktree rm --worktree branch:feat/X-1-a",
            f"cd {main_repo} && orca worktree rm --worktree id:r::{wt}",
            f"git worktree remove {wt}",
            f"git -C {main_repo} worktree remove {wt}",
            f"git worktree remove --force {wt}",
            f"rm -rf {wt}",
            f"bash -c 'orca worktree rm --worktree id:r::{wt}'",
        ]
        allowed = [
            "orca worktree list --json", "orca worktree ps --json", "orca terminal list --worktree id:r::/x",
            "git worktree list", "git worktree add ../y", "git worktree prune", "git status", "rm -rf /tmp/some-unrelated-dir",
            "echo orca worktree rm --worktree x", "git commit -m \"orca worktree rm\"", "cat <<'EOF'\norca worktree rm --worktree x\nEOF",
            f"orca worktree rm --worktree id:r::{base}/gone",   # already gone: nothing to lose
        ]
        for c in blocked:
            assert D(c), f"should block: {c!r}"
        for c in allowed:
            assert not D(c), f"should allow: {c!r}"
        assert D("orca worktree rm --json")                       # no selector: cannot tell which, blocked
        assert "check" in D(f"git worktree remove {wt}") and "--user-approved" in D(f"git worktree remove {wt}")
        # a fresh clearance lets the same removals through; an override env too
        assert clearance.main(["grant", str(wt)]) == 0
        for c in blocked:
            assert not D(c), f"cleared, should allow: {c!r}"
        (wt / "dirty.txt").write_text("x")
        os.remove(base / "clr" / clearance.key(wt))
        assert D(f"git worktree remove {wt}") and clearance.main(["grant", str(wt)]) == 3 and D(f"git worktree remove {wt}")
        assert not D(f"git worktree remove {wt}", e={"SHIPKIT_ALLOW_WORKTREE_RM": "1"})
        assert clearance.main(["grant", str(wt), "--user-approved"]) == 0 and not D(f"rm -rf {wt}")
        print("worktree-delete-guard: self-test ok")
        return 0
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)


def main():
    if "--self-test" in sys.argv:
        return self_test()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if event.get("tool_name") != "Bash":
        return
    msg = decide((event.get("tool_input") or {}).get("command", ""), event.get("cwd") or os.getcwd(), os.environ)
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())
