#!/usr/bin/env python3
"""Post/delete Jira comments with REAL @mentions via REST API v3 (ADF).

The Atlassian MCP addCommentToJiraIssue stores mentions as plain text (nobody is notified).

  python3 jira-comment.py post <TICKET> (--file PATH | -) [--dry-run]
  python3 jira-comment.py delete <TICKET> <COMMENT_ID>
  python3 jira-comment.py --self-test

Env: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN (the token is never printed).
Exit: 0 ok, 2 bad usage, 3 env missing, 4 Jira rejected, 5 posted but a mention did not come back.

Markdown subset: @[Name](accountId)  @[](accountId) (name looked up)  **bold**  `code`
[text](https://url)  "- " bullets  "1. " ordered  "# " headings  blank line = paragraph,
single newline = hard break.
"""
import base64, json, os, re, sys, urllib.error, urllib.parse, urllib.request

INLINE = re.compile(
    r"@\[(?P<mn>[^\]]*)\]\((?P<mid>[^)\s]+)\)"
    r"|\*\*(?P<b>.+?)\*\*"
    r"|`(?P<c>[^`]+)`"
    r"|\[(?P<lt>[^\]]+)\]\((?P<lu>https?://[^)\s]+)\)"
)


def text(s, marks=None):
    n = {"type": "text", "text": s}
    if marks:
        n["marks"] = marks
    return n


def inline(s, names):
    out, pos = [], 0
    for m in INLINE.finditer(s):
        if m.start() > pos:
            out.append(text(s[pos:m.start()]))
        if m.group("mid"):
            name = m.group("mn") or names(m.group("mid"))
            out.append({"type": "mention", "attrs": {"id": m.group("mid"), "text": "@" + name.lstrip("@")}})
        elif m.group("b"):
            out.append(text(m.group("b"), [{"type": "strong"}]))
        elif m.group("c"):
            out.append(text(m.group("c"), [{"type": "code"}]))
        else:
            out.append(text(m.group("lt"), [{"type": "link", "attrs": {"href": m.group("lu")}}]))
        pos = m.end()
    if pos < len(s):
        out.append(text(s[pos:]))
    return out


def lines_inline(lines, names):
    out = []
    for i, ln in enumerate(lines):
        if i:
            out.append({"type": "hardBreak"})
        out += inline(ln, names)
    return out


def build_adf(md, names):
    blocks = []
    for chunk in re.split(r"\n\s*\n", md.strip()):
        ls = chunk.split("\n")
        kind = pat = None
        if all(re.match(r"- ", l) for l in ls):
            kind, pat = "bulletList", r"- "
        elif all(re.match(r"\d+\. ", l) for l in ls):
            kind, pat = "orderedList", r"\d+\. "
        if kind:
            items = [{"type": "listItem", "content": [{"type": "paragraph", "content": inline(re.sub("^" + pat, "", l), names)}]} for l in ls]
            blocks.append({"type": kind, "content": items})
            continue
        h = re.match(r"(#{1,6}) (.*)", ls[0])
        if h:
            blocks.append({"type": "heading", "attrs": {"level": len(h.group(1))}, "content": inline(h.group(2), names)})
            ls = ls[1:]
            if not ls:
                continue
        blocks.append({"type": "paragraph", "content": lines_inline(ls, names)})
    return {"version": 1, "type": "doc", "content": blocks}


def mention_ids(node):
    if isinstance(node, dict):
        if node.get("type") == "mention":
            yield node.get("attrs", {}).get("id")
        for v in node.values():
            yield from mention_ids(v)
    elif isinstance(node, list):
        for v in node:
            yield from mention_ids(v)


def die(code, msg):
    print(msg, file=sys.stderr)
    sys.exit(code)


def env():
    v = {k: os.environ.get(k, "") for k in ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")}
    miss = [k for k, x in v.items() if not x]
    if miss:
        die(3, "missing env: " + ", ".join(miss) + " (MCP fallback will NOT notify mentioned people)")
    v["JIRA_URL"] = v["JIRA_URL"].rstrip("/")
    return v


def call(method, path, body=None):
    e = env()
    auth = base64.b64encode(f"{e['JIRA_EMAIL']}:{e['JIRA_API_TOKEN']}".encode()).decode()
    req = urllib.request.Request(
        e["JIRA_URL"] + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Basic " + auth, "Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as ex:
        die(4, f"Jira {method} {path} -> HTTP {ex.code}: {ex.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as ex:
        die(4, f"Jira {method} {path} failed: {ex.reason}")


def display_name(account_id):
    return call("GET", "/rest/api/3/user?accountId=" + urllib.parse.quote(account_id)).get("displayName") or account_id


def check_ticket(t):
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", t):
        die(2, f"bad ticket id: {t!r}")


def cmd_post(args):
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if len(args) == 2 and args[1] == "-":
        src = None
    elif len(args) == 3 and args[1] == "--file":
        src = args[2]
    else:
        die(2, "usage: post <TICKET> (--file PATH | -) [--dry-run]")
    check_ticket(args[0])
    try:
        md = sys.stdin.read() if src is None else open(src).read()
    except OSError as ex:
        die(2, f"cannot read {src}: {ex}")
    if not md.strip():
        die(2, "empty comment body")
    adf = build_adf(md, (lambda i: i) if dry else display_name)
    if dry:
        print(json.dumps(adf, indent=2, ensure_ascii=False))
        return
    want = list(mention_ids(adf))
    res = call("POST", f"/rest/api/3/issue/{args[0]}/comment", {"body": adf})
    got = set(mention_ids(res.get("body")))
    cid = res.get("id")
    print(json.dumps({"id": cid, "url": f"{env()['JIRA_URL']}/browse/{args[0]}?focusedCommentId={cid}", "mentions": sorted(got)}))
    missing = [i for i in want if i not in got]
    if missing:
        die(5, f"posted comment {cid} but mention(s) did not come back as mention nodes: {', '.join(missing)}")


def cmd_delete(args):
    if len(args) != 2 or not args[1].isdigit():
        die(2, "usage: delete <TICKET> <COMMENT_ID>")
    check_ticket(args[0])
    call("DELETE", f"/rest/api/3/issue/{args[0]}/comment/{args[1]}")
    print(json.dumps({"deleted": args[1]}))


def self_test():
    d = build_adf(
        "# Title\n\nHi @[Ann](a:1) and @[](b:2), **bold** `x` [l](https://e.co)\nnext line\n\n- one\n- two\n\n1. a\n2. b",
        lambda i: "Looked Up" if i == "b:2" else i,
    )
    c = d["content"]
    assert [b["type"] for b in c] == ["heading", "paragraph", "bulletList", "orderedList"], c
    assert list(mention_ids(d)) == ["a:1", "b:2"]
    p = c[1]["content"]
    assert p[1] == {"type": "mention", "attrs": {"id": "a:1", "text": "@Ann"}}
    assert p[3]["attrs"]["text"] == "@Looked Up"
    assert any(n.get("marks") == [{"type": "strong"}] for n in p)
    assert any(n.get("marks") == [{"type": "code"}] for n in p)
    assert any(n.get("marks", [{}])[0].get("type") == "link" for n in p)
    assert {"type": "hardBreak"} in p
    assert len(c[2]["content"]) == 2 and len(c[3]["content"]) == 2
    print("self-test ok")


def main():
    a = sys.argv[1:]
    if a == ["--self-test"]:
        return self_test()
    if a and a[0] == "post":
        return cmd_post(a[1:])
    if a and a[0] == "delete":
        return cmd_delete(a[1:])
    die(2, __doc__)


if __name__ == "__main__":
    main()
