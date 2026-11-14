#!/usr/bin/env python3
"""set-output-style.py — set, clear or show `outputStyle` in a Claude Code settings file; every other key stays.

  python3 -I scripts/set-output-style.py <style>   [--scope local|project|user] [--dir D]
  python3 -I scripts/set-output-style.py <style> --keep-existing              # only if no style is chosen yet (unset or "default"); /bootstrap uses this
  python3 -I scripts/set-output-style.py --clear   [--scope ...] [--dir D]    # removes the key (not the same as "default")
  python3 -I scripts/set-output-style.py --show    [--dir D]                  # the value in each of the three files

  --scope local    (default) <root>/.claude/settings.local.json — yours only; stays out of git
  --scope project  <dir>/.claude/settings.json                  — commit it and the team gets it
  --scope user     ~/.claude/settings.json                      — every project on this machine
  --dir D          the project (default: the current directory)

`<root>` for `local` is the main checkout's root, also when --dir is inside a worktree: Claude Code reads and writes the local file
there (docs: settings → "Where Claude Code keeps the local file"). Outside git, or when that root is the home directory, it is --dir.
Not covered: Windows, and a repository root owned by another user (Claude Code keeps the file in --dir there too).

The style name is case-sensitive and must match exactly; a wrong name silently gives the default style. A running session
picks the edit up from the next message. Unparseable JSON is never overwritten: exit 1, file untouched.
Exit: 0 done (or already so), 1 settings file unreadable, 2 usage.   python3 -I scripts/set-output-style.py --self-test
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

KEY = "outputStyle"


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def settings_path(scope, directory):
    d = Path(directory).resolve()
    if scope == "user":
        return Path.home() / ".claude" / "settings.json"
    if scope == "project":
        return d / ".claude" / "settings.json"
    common = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], d)
    root = Path(common).parent if common.endswith(".git") else d
    return (d if root == Path.home() else root) / ".claude" / "settings.local.json"


def load(path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text() or "{}")
    except ValueError as e:
        sys.exit(f"{path}: not valid JSON ({e}); left untouched")
    if not isinstance(data, dict):
        sys.exit(f"{path}: top level is not an object; left untouched")
    return data


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".settings-", suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def apply(scope, directory, style, keep_existing=False):
    """style None = clear. keep_existing: leave a style the user already chose (anything but unset / "default"). Returns (path, message)."""
    path = settings_path(scope, directory)
    data = load(path)
    if style is None:
        if KEY not in data:
            return path, f"{path}: {KEY} already unset"
        del data[KEY]
    elif data.get(KEY) == style:
        return path, f"{path}: {KEY} already {style!r}"
    elif keep_existing and data.get(KEY, "default") != "default":
        return path, f"{path}: {KEY} kept as {data[KEY]!r}"
    else:
        data[KEY] = style
    write(path, data)
    return path, f"{path}: {KEY} {'cleared' if style is None else 'set to ' + repr(style)}"


def main(argv):
    scope, directory, style, mode, keep = "local", os.getcwd(), None, "set", False
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--scope" and args and args[0] in ("local", "project", "user"):
            scope = args.pop(0)
        elif a == "--keep-existing":
            keep = True
        elif a == "--dir" and args:
            directory = args.pop(0)
        elif a in ("--clear", "--show"):
            mode = a[2:]
        elif a in ("-h", "--help"):
            print(__doc__); return 0
        elif not a.startswith("-") and style is None and mode == "set":
            style = a
        else:
            print(f"unknown argument: {a} (try --help)", file=sys.stderr); return 2
    if mode == "set" and not style:
        print("give a style name, --clear or --show (try --help)", file=sys.stderr); return 2
    if mode == "show":
        for s in ("local", "project", "user"):
            p = settings_path(s, directory)
            print(f"{s}: {load(p).get(KEY, 'unset')}  ({p})")
        return 0
    path, msg = apply(scope, directory, None if mode == "clear" else style, keep)
    print(msg)
    if scope == "local" and mode == "set" and subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=path.parent, stderr=subprocess.DEVNULL).returncode == 1:
        print(f"note: {path} is not git-ignored here; add **/.claude/settings.local.json to .gitignore", file=sys.stderr)
    return 0


def self_test():
    import shutil
    # a git hook (pre-commit runs self-test.sh) sets GIT_INDEX_FILE / GIT_DIR; the scratch repos below must not inherit them
    for k in [k for k in os.environ if k.startswith("GIT_")]:
        del os.environ[k]
    base = Path(tempfile.mkdtemp())
    try:
        proj = base / "proj"; proj.mkdir()
        # fresh file is created, other keys of an existing one survive
        loc = proj / ".claude" / "settings.local.json"
        assert main(["shipkit", "--scope", "project", "--dir", str(proj)]) == 0
        assert json.loads((proj / ".claude" / "settings.json").read_text()) == {KEY: "shipkit"}
        loc.parent.mkdir(exist_ok=True)
        loc.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}, KEY: "default"}))
        # not a git repo: local file is in --dir
        assert main(["shipkit", "--dir", str(proj)]) == 0
        assert json.loads(loc.read_text()) == {"permissions": {"allow": ["Bash(ls)"]}, KEY: "shipkit"}
        # idempotent: no rewrite
        before = loc.stat().st_mtime_ns
        assert apply("local", proj, "shipkit")[1].endswith("already 'shipkit'") and loc.stat().st_mtime_ns == before
        # --keep-existing: a chosen style stays, "default" or unset is replaced
        loc.write_text(json.dumps({KEY: "Concise"}))
        assert apply("local", proj, "shipkit", True)[1].endswith("kept as 'Concise'") and json.loads(loc.read_text()) == {KEY: "Concise"}
        loc.write_text(json.dumps({KEY: "default"}))
        assert main(["shipkit", "--keep-existing", "--dir", str(proj)]) == 0 and json.loads(loc.read_text()) == {KEY: "shipkit"}
        loc.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}, KEY: "shipkit"}))
        # clear removes only the key; clearing again is a no-op
        assert main(["--clear", "--dir", str(proj)]) == 0
        assert json.loads(loc.read_text()) == {"permissions": {"allow": ["Bash(ls)"]}}
        assert apply("local", proj, None)[1].endswith("already unset")
        # broken JSON is never overwritten
        loc.write_text("{ nope")
        try:
            main(["x", "--dir", str(proj)]); assert False, "should exit"
        except SystemExit as e:
            assert e.code != 0 and "not valid JSON" in str(e.code)
        assert loc.read_text() == "{ nope"
        # usage errors
        assert main([]) == 2 and main(["--scope", "bogus", "x"]) == 2 and main(["a", "b"]) == 2
        # a worktree writes the main checkout's local file
        if shutil.which("git"):
            repo = base / "repo"; repo.mkdir()
            env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", **os.environ}
            for cmd in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "i"], ["worktree", "add", "-q", str(base / "wt"), "-b", "w"]):
                subprocess.run(["git", *cmd], cwd=repo, env=env, check=True, capture_output=True)
            assert main(["shipkit", "--dir", str(base / "wt")]) == 0
            assert (repo / ".claude" / "settings.local.json").exists() and not (base / "wt" / ".claude").exists()
            assert settings_path("local", base / "wt").resolve() == (repo / ".claude" / "settings.local.json").resolve()
        print("set-output-style self-test: ok")
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main(sys.argv[1:]))
