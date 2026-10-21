#!/usr/bin/env python3
"""Lint every skills/*/SKILL.md frontmatter against the skill-authoring guidance.

Usage: python3 -I scripts/check-skills.py [--self-test]      exit 0 ok · 1 findings
Checks: `name` equals the directory; `description` is present, starts with "Use when", is <= 1024 characters, and gives
a Trigger line only when the skill takes arguments; a skill whose Trigger shows arguments has an `argument-hint`.
Also checks that every `${CLAUDE_PLUGIN_ROOT}/…` file a SKILL.md or reference points at exists.
A skill whose files call post-slack.js or jira-comment.py must point at references/write-through-scripts.md.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_DESC = 1024

def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        v = v.strip()
        fm[k.strip()] = json.loads(v) if v.startswith('"') else v
    return fm

def lint(skill_dir, text):
    out = []
    fm = frontmatter(text)
    if fm is None:
        return ["no frontmatter"]
    if fm.get("name") != skill_dir:
        out.append(f"name {fm.get('name')!r} != directory {skill_dir!r}")
    d = fm.get("description", "")
    if not d:
        out.append("no description")
    else:
        if not d.lower().startswith("use when"):
            out.append("description does not start with 'Use when'")
        if len(d) > MAX_DESC:
            out.append(f"description is {len(d)} chars (max {MAX_DESC})")
        trig = re.search(r"Trigger: /[\w:-]+ (\S.*?)(\.|$)", d)
        if trig and "argument-hint" not in fm:
            out.append("Trigger shows arguments but there is no argument-hint")
    return out

def missing_refs(text):
    return [p for p in sorted(set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+\.(?:json|js|md|sh|py|txt|swift))", text)))
            if not (ROOT / p).exists()]

def writes_lint(texts):
    """A skill whose files call a Slack/Jira write script must point at the shared rule for writing through scripts."""
    if re.search(r"jira-comment\.py|post-slack\.js", texts) and "write-through-scripts.md" not in texts:
        return ["calls post-slack.js / jira-comment.py but never points at references/write-through-scripts.md"]
    return []

def self_test():
    good = '---\nname: x\ndescription: "Use when a thing. Trigger: /x <t>"\nargument-hint: "<t>"\n---\nbody\n'
    assert lint("x", good) == []
    assert lint("y", good) == ["name 'x' != directory 'y'"]
    assert "description does not start with 'Use when'" in lint("x", good.replace("Use when", "Does"))
    assert any("argument-hint" in f for f in lint("x", good.replace('argument-hint: "<t>"\n', "")))
    assert any("chars" in f for f in lint("x", good.replace("a thing", "a" * 1100)))
    assert missing_refs("see ${CLAUDE_PLUGIN_ROOT}/scripts/nope-xyz.sh and ${CLAUDE_PLUGIN_ROOT}/scripts/probe.sh") == ["scripts/nope-xyz.sh"]
    assert writes_lint("run post-slack.js") != [] and writes_lint("jira-comment.py post") != []
    assert writes_lint("run post-slack.js; see references/write-through-scripts.md") == [] and writes_lint("no writes here") == []
    print("check-skills: self-test ok")

def main():
    if "--self-test" in sys.argv:
        return self_test()
    bad = 0
    files = sorted(set((ROOT / "skills").glob("*/*.md")) | set((ROOT / "references").glob("*.md")))
    for f in files:
        text = f.read_text()
        out = lint(f.parent.name, text) if f.name == "SKILL.md" else []
        if f.name == "SKILL.md":
            out += writes_lint("\n".join(p.read_text() for p in sorted(f.parent.glob("*.md"))))
        out += [f"points at missing file ${{CLAUDE_PLUGIN_ROOT}}/{p}" for p in missing_refs(text)]
        rel = f.relative_to(ROOT)
        if out:
            bad += 1
            print(f"FAIL {rel}")
            for o in out:
                print(f"       {o}")
    print(f"{'ok  ' if not bad else 'FAIL'} check-skills: {len(files)} files, {bad} with findings")
    sys.exit(1 if bad else 0)

main()
