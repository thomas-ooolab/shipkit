#!/usr/bin/env python3
"""Which language does this user want to be answered in?

Read from what the user already said, never guessed. First hit wins:
  1. `language:` in `.shipkit/config.yml` (this checkout, then the primary checkout) — the user set it on purpose.
  2. Auto-memory from earlier sessions: `<claude dir>/projects/<primary path, / and . -> ->/memory/*.md` first, then the
     memory of the user's other projects (never the throwaway scratchpad ones); within a group the newest file first. A line
     counts when it names a language right after a cue about talking to the user ("ask questions in Vietnamese",
     "replies in Vietnamese", "hỏi lại tiếng việt đi"); "code and commits stay English" has no cue and is not read.
Nothing found -> `language: unknown`: the caller uses the language of the user's own message, else English.

  user-language.py [<dir>] [--claude-dir <dir>]   print language / source / evidence lines (exit 0 always)
  user-language.py --hook                         SessionStart hook: JSON on stdout when a language is known, else silent
  user-language.py --self-test

Read-only. Exit 0 whatever it finds: a missing language is an answer, not an error.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LANGS = {"vietnamese": "vi", "english": "en", "japanese": "ja", "korean": "ko", "chinese": "zh", "french": "fr",
         "german": "de", "spanish": "es", "thai": "th", "indonesian": "id", "portuguese": "pt", "russian": "ru"}
VI_LANGS = {"việt": "vietnamese", "anh": "english", "nhật": "japanese", "hàn": "korean", "trung": "chinese",
            "pháp": "french", "đức": "german"}
CUE = (r"(?:ask|asks|answer|answers|reply|replies|respond|responds|speak|speaks|talk|talks|questions?|messages?|"
       r"requests?|summar(?:y|ies)|chat|writes)")
EN_RE = re.compile(rf"\b{CUE}\b[^.;\n]{{0,80}}?\b(?:in|using)\s+({'|'.join(LANGS)})\b", re.I)
VI_RE = re.compile(rf"(?:trả lời|hỏi|nói|viết|dùng|giao tiếp)[^.;\n]{{0,80}}?tiếng\s+({'|'.join(VI_LANGS)})\b", re.I)


def git_root(d):
    """(this checkout's top, the primary checkout's top) — the same path outside a linked worktree."""
    def run(*a):
        r = subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    top = run("rev-parse", "--show-toplevel")
    common = run("rev-parse", "--path-format=absolute", "--git-common-dir")
    top = Path(top) if top else Path(d).resolve()
    primary = Path(common).parent if common.endswith("/.git") else top
    return top, primary


def from_config(roots):
    for root in roots:
        f = root / ".shipkit" / "config.yml"
        if f.is_file():
            for line in f.read_text(errors="replace").splitlines():
                m = re.match(r"language:\s*([A-Za-z-]+)\s*(?:#.*)?$", line)
                if m:
                    return m.group(1).lower(), str(f), line.strip()
    return None


def match(line):
    """The language named by one line, as (code, name, the words that named it) or None."""
    m = EN_RE.search(line)
    if m:
        name = m.group(1).lower()
        return LANGS[name], name, m.group(0)
    m = VI_RE.search(line)
    if m:
        name = VI_LANGS[m.group(1).lower()]
        return LANGS[name], name, m.group(0)
    return None


def memory_files(claude_dir, primary):
    projects = claude_dir / "projects"
    own = projects / re.sub(r"[/.]", "-", str(primary)) / "memory"

    def newest(d):
        files = [p for p in d.glob("*.md") if p.name != "MEMORY.md"] if d.is_dir() else []
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    others = [d / "memory" for d in projects.glob("*") if d / "memory" != own and "scratchpad" not in d.name
              and "private-tmp" not in d.name] if projects.is_dir() else []
    rest = [f for d in others for f in newest(d)]
    return newest(own) + sorted(rest, key=lambda p: p.stat().st_mtime, reverse=True)


def from_memory(claude_dir, primary):
    hits = []
    for f in memory_files(claude_dir, primary):
        for line in f.read_text(errors="replace").splitlines():
            m = match(line)
            if m:
                hits.append((m[0], m[1], str(f), m[2]))
                break
    return hits


def detect(d, claude_dir):
    top, primary = git_root(d)
    cfg = from_config([top] if top == primary else [top, primary])
    if cfg:
        return {"code": cfg[0], "name": cfg[0], "source": f"config {cfg[1]}", "evidence": cfg[2], "also": []}
    hits = from_memory(claude_dir, primary)
    if hits:
        c, n, f, ev = hits[0]
        return {"code": c, "name": n.capitalize(), "source": f"memory {f}", "evidence": ev,
                "also": sorted({h[0] for h in hits} - {c})}
    return None


def render(r):
    if not r:
        return ("language: unknown\nsource: none — `language:` is unset in .shipkit/config.yml and no memory file names one; "
                "use the language of the user's own message, else English")
    s = f"language: {r['code']} ({r['name']})\nsource: {r['source']}\nevidence: {r['evidence']}"
    return s + (f"\nalso named in older or other memory: {', '.join(r['also'])}" if r["also"] else "")


def hook(claude_dir):
    try:
        cwd = json.load(sys.stdin).get("cwd") or os.getcwd()
    except Exception:
        cwd = os.getcwd()
    r = detect(cwd, claude_dir)
    if r:
        ctx = (f"Language for everything you say to this user (questions, reports, summaries, drafts for them): "
               f"{r['name']} ({r['code']}), from {r['source']}: \"{r['evidence'][:300]}\". Pass `language: {r['code']}` "
               f"to every agent or worker you start. Code, commits, skill files and text posted to Jira or Slack follow their own language rules, not this one.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))


def self_test():
    for k in [k for k in os.environ if k.startswith("GIT_")]:
        del os.environ[k]  # run from a git hook (pre-commit) they point every git call at the committing repo
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + label)
        ok = ok and cond

    with tempfile.TemporaryDirectory() as t:
        t = Path(t).resolve()
        repo, claude = t / "my.repo", t / "claude"
        repo.mkdir()
        for a in (["init", "-q"], ["config", "user.email", "a@b"], ["config", "user.name", "a"],
                  ["commit", "-q", "--allow-empty", "-m", "x"]):
            subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
        key = re.sub(r"[/.]", "-", str(repo))

        def mem(project, name, text, age=0):
            f = claude / "projects" / project / "memory" / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
            os.utime(f, (time.time() - age, time.time() - age))

        check("nothing known -> unknown", detect(repo, claude) is None and "language: unknown" in render(None))
        mem(key, "a.md", "Ask clarifying questions and write options in Vietnamese. Code, commits stay English.")
        r = detect(repo, claude)
        check("memory: questions in Vietnamese -> vi", r and r["code"] == "vi" and "a.md" in r["source"])
        mem(key, "a.md", "- user: Task text pasted in English still means skill files stay English; code stays English.")
        check("a line with no cue (stay English) is not read", detect(repo, claude) is None)
        mem(key, "a.md", "hỏi lại tiếng việt đi")
        check("Vietnamese-written line -> vi", (detect(repo, claude) or {}).get("code") == "vi")
        mem(key, "b.md", "Chat replies go in Japanese.", age=-10)
        r = detect(repo, claude)
        check("the newest file of the project wins, the other language is listed", r["code"] == "ja" and r["also"] == ["vi"])
        mem("-other-project", "c.md", "Always reply in German.", age=-100)
        check("own project's memory beats a newer one elsewhere", detect(repo, claude)["code"] == "ja")
        (claude / "projects" / key / "memory" / "a.md").unlink()
        (claude / "projects" / key / "memory" / "b.md").unlink()
        check("another project's memory is used when the project has none", detect(repo, claude)["code"] == "de")
        mem("-private-tmp-x-scratchpad-arm", "d.md", "Always reply in French.", age=-500)
        check("throwaway scratchpad projects are ignored", detect(repo, claude)["code"] == "de")
        (repo / ".shipkit").mkdir()
        (repo / ".shipkit" / "config.yml").write_text("# language: fr\n")
        check("a commented config line is not read", detect(repo, claude)["code"] == "de")
        (repo / ".shipkit" / "config.yml").write_text("language: vi   # questions and drafts\n")
        r = detect(repo, claude)
        check("config language beats memory", r["code"] == "vi" and r["source"].startswith("config"))
        wt = t / "wt"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(wt)], check=True, capture_output=True)
        check("a linked worktree reads the primary checkout's config", detect(wt, claude)["code"] == "vi")
        (repo / ".shipkit" / "config.yml").unlink()
        mem(key, "e.md", "Reply in Vietnamese.")
        check("a linked worktree reads the primary project's memory", detect(wt, claude)["code"] == "vi")
        out = subprocess.run([sys.executable, "-I", __file__, "--hook", "--claude-dir", str(claude)], input=json.dumps(
            {"cwd": str(wt)}), capture_output=True, text=True)
        j = json.loads(out.stdout)
        check("hook prints SessionStart JSON naming the language", out.returncode == 0 and "Vietnamese (vi)" in
              j["hookSpecificOutput"]["additionalContext"])
        (claude / "projects" / key / "memory" / "e.md").unlink()
        (claude / "projects" / "-other-project" / "memory" / "c.md").unlink()
        out = subprocess.run([sys.executable, "-I", __file__, "--hook", "--claude-dir", str(claude)], input="{}",
                             capture_output=True, text=True, cwd=str(t))
        check("hook is silent when nothing is known", out.returncode == 0 and out.stdout == "")
    print("self-test " + ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    if "--claude-dir" in argv:
        i = argv.index("--claude-dir")
        claude = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if "--hook" in argv:
        hook(claude)
        return 0
    print(render(detect(argv[0] if argv else os.getcwd(), claude)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
