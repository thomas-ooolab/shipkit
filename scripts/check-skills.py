#!/usr/bin/env python3
"""Lint every skills/*/SKILL.md frontmatter against the skill-authoring guidance.

Usage: python3 -I scripts/check-skills.py [--self-test]      exit 0 ok · 1 findings
Checks: `name` equals the directory; `description` is present, starts with "Use when", is <= 1024 characters, and gives
a Trigger line only when the skill takes arguments; a skill whose Trigger shows arguments has an `argument-hint`.
Also checks that every `${CLAUDE_PLUGIN_ROOT}/…` file a SKILL.md or reference points at exists.
A skill whose files call post-slack.js or jira-comment.py must point at references/write-through-scripts.md.
A skill that has an agent drive a browser must point at references/browser-agents.md and scripts/cleanup-browsers.sh.
The skills in SCOPED (pr, assign, bugfix) must point at references/scoped-tests.md.
The files in BORROWED must keep the "borrowed capability not found" warning to the dev (a capability owned by another ticket is verified, not assumed).
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

BORROWED = ["references/open-question-options.md", "references/jira-comment-rules.md", "skills/cross-check/SKILL.md",
            "skills/plan-deep/SKILL.md", "skills/spec-from-ticket/SKILL.md", "skills/clarify/SKILL.md"]

def borrowed_lint(texts):
    """Each file in BORROWED must still tell the dev "borrowed capability not found" before relying on another ticket's capability; texts maps path -> text."""
    return [f"{p} lost the 'borrowed capability not found' warning" for p in BORROWED
            if "borrowed capability not found" not in " ".join(texts.get(p, "").lower().replace("*", "").split())]

SCOPED = ["skills/pr/SKILL.md", "skills/assign/SKILL.md", "skills/bugfix/SKILL.md"]

def scoped_lint(texts):
    """The skills that run tests must point at the shared scoped-tests rule, not run the whole suite on their own."""
    return [f"{p} runs tests but never points at references/scoped-tests.md" for p in SCOPED if "scoped-tests.md" not in texts.get(p, "")]

BROWSER_SKILLS = {"verify", "design-recon", "assign", "bugfix", "run-pipeline"}

def transport_lint(text):
    """/assign's SKILL.md must keep the transport gate: print + record the `transport:` line first, and no Agent tool in an Orca worktree."""
    need = ("Step 1.5 — Transport gate", "transport: orca (worktree", "transport: agent (reason", "Orca worktree present = Orca workers, always", "forbidden for dispatch")
    return [f"skills/assign/SKILL.md lost the transport gate text '{w}'" for w in need if w not in text]

def reuse_lint(orca_mode, skill):
    """Terminal reuse in /assign is for every agent kind, called without --agent/--model/--effort; the old 'kiro only' sentence must not come back."""
    out = [f"skills/assign/orca-mode.md lost '{w}'" for w in ("Reuse is tried for every agent kind", "Never add `--agent`, `--model` or `--effort`", "`Idle close:` line") if w not in orca_mode]
    out += [f"skills/assign/{n} still says '{w}'" for n, t in (("orca-mode.md", orca_mode), ("SKILL.md", skill)) for w in ("claude has none", "Kiro terminals only") if w in t]
    return out + ([] if "every agent kind" in skill else ["skills/assign/SKILL.md lost 'every agent kind' in the Find-before-you-create gotcha"])

REVIEW_LOOP_RULES = ("Severity stop", "one** `/assign` pass", "sweep the PR's diff", "Already answered, do not raise again",
                     "full review <links>", "only at a decision point", "not a stall")

def review_loop_lint(loop, config):
    """/pr's review loop keeps its rules for the bot (no memory, slow, nit-by-nit): severity stop, one batched fix pass with a sweep, answered items re-sent, status line is not a verdict, quiet reporting, a wait longer than a real review."""
    out = [f"skills/pr/review-loop.md lost '{r}'" for r in REVIEW_LOOP_RULES if r not in loop]
    if config.get("waiter", {}).get("default_timeout_minutes", 0) < 20:
        out.append("skills/pr/config.json waiter.default_timeout_minutes is below 20 (a full review takes 12-15 minutes)")
    return out

def browser_lint(name, texts):
    """A skill that has an agent drive a browser must point at the rules and at the cleanup script (stopping an agent does not stop its browsers)."""
    if (name in BROWSER_SKILLS or re.search(r"playwright|browser_navigate|chrome-headless", texts, re.I)) and not all(
            w in texts for w in ("references/browser-agents.md", "scripts/cleanup-browsers.sh")):
        return ["drives a browser but does not point at references/browser-agents.md and scripts/cleanup-browsers.sh"]
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
    assert borrowed_lint({p: "⚠ borrowed capability\nnot found: X" for p in BORROWED}) == [] and len(borrowed_lint({})) == len(BORROWED)
    assert scoped_lint({p: "see references/scoped-tests.md" for p in SCOPED}) == [] and len(scoped_lint({})) == len(SCOPED)
    both = "references/browser-agents.md scripts/cleanup-browsers.sh"
    gate = "Step 1.5 — Transport gate transport: orca (worktree transport: agent (reason Orca worktree present = Orca workers, always forbidden for dispatch"
    assert transport_lint(gate) == [] and len(transport_lint("")) == 5 and transport_lint(gate.replace("forbidden for dispatch", "")) != []
    ok_o, ok_s = "Reuse is tried for every agent kind. Never add `--agent`, `--model` or `--effort`. `Idle close:` line", "every agent kind"
    assert reuse_lint(ok_o, ok_s) == [] and len(reuse_lint("", "")) == 4 and reuse_lint(ok_o + " claude has none", ok_s) != [] and reuse_lint(ok_o, "") != []
    assert review_loop_lint(" ".join(REVIEW_LOOP_RULES), {"waiter": {"default_timeout_minutes": 20}}) == []
    assert len(review_loop_lint("", {})) == len(REVIEW_LOOP_RULES) + 1 and review_loop_lint(" ".join(REVIEW_LOOP_RULES), {"waiter": {"default_timeout_minutes": 10}}) != []
    assert browser_lint("verify", "") != [] and browser_lint("x", "uses Playwright") != [] and browser_lint("x", "uses Playwright " + both) == []
    assert browser_lint("x", "no browsers here") == [] and browser_lint("assign", both) == [] and browser_lint("assign", "references/browser-agents.md") != []
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
            dir_texts = "\n".join(p.read_text() for p in sorted(f.parent.glob("*.md")))
            out += writes_lint(dir_texts) + browser_lint(f.parent.name, dir_texts)
        out += [f"points at missing file ${{CLAUDE_PLUGIN_ROOT}}/{p}" for p in missing_refs(text)]
        rel = f.relative_to(ROOT)
        if out:
            bad += 1
            print(f"FAIL {rel}")
            for o in out:
                print(f"       {o}")
    texts = {p: (ROOT / p).read_text() for p in BORROWED + SCOPED if (ROOT / p).exists()}
    lost = borrowed_lint(texts) + scoped_lint(texts) + transport_lint(texts.get("skills/assign/SKILL.md", ""))
    lost += review_loop_lint((ROOT / "skills/pr/review-loop.md").read_text(), json.loads((ROOT / "skills/pr/config.json").read_text()))
    lost += reuse_lint((ROOT / "skills/assign/orca-mode.md").read_text(), texts.get("skills/assign/SKILL.md", ""))
    for o in lost:
        bad += 1
        print(f"FAIL {o}")
    print(f"{'ok  ' if not bad else 'FAIL'} check-skills: {len(files)} files, {bad} with findings")
    sys.exit(1 if bad else 0)

main()
