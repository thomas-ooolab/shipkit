#!/usr/bin/env python3
"""Post/edit/delete Jira comments with REAL @mentions and inline images via REST API v3 (ADF).

The Atlassian MCP addCommentToJiraIssue stores mentions as plain text (nobody is notified).

  python3 jira-comment.py post <TICKET> (--file PATH | -) [--image PATH[:CAPTION]]... [--dry-run]
  python3 jira-comment.py edit <TICKET> <COMMENT_ID> (--file PATH | -) [--image PATH[:CAPTION]]... [--dry-run]
  python3 jira-comment.py delete <TICKET> <COMMENT_ID>
  python3 jira-comment.py --self-test

Env: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN (the token is never printed).
Exit: 0 ok, 2 bad usage, 3 env missing, 4 Jira rejected (incl. failed upload / media lookup),
5 posted but a mention did not come back.

Markdown subset: @[Name](accountId)  @[](accountId) (name looked up)  **bold**  `code`
[text](https://url)  "- " bullets  "1. " ordered  "# " headings  blank line = paragraph,
single newline = hard break.
Images: a line `![caption](/abs/path.png)` becomes an inline image (italic caption paragraph above
it); `--image PATH[:CAPTION]` appends images at the end. Each file is uploaded once as an issue
attachment, then embedded. --dry-run uploads nothing: it prints the ADF and lists the files.
`edit` replaces the comment body in place without re-notifying (notifyUsers=false).
"""
import base64, json, os, re, struct, sys, urllib.error, urllib.parse, urllib.request, uuid

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


IMG_LINE = re.compile(r"!\[(?P<cap>[^\]]*)\]\((?P<path>[^)\s][^)]*)\)")


def image_blocks(cap, media):
    """media = (uuid, width, height). Caption (if any) is an italic paragraph above the image."""
    out = []
    if cap:
        out.append({"type": "paragraph", "content": [text(cap, [{"type": "em"}])]})
    out.append({"type": "mediaSingle", "attrs": {"layout": "center"}, "content": [
        {"type": "media", "attrs": {"type": "file", "id": media[0], "collection": "", "width": media[1], "height": media[2]}}]})
    return out


def lines_inline(lines, names):
    out = []
    for i, ln in enumerate(lines):
        if i:
            out.append({"type": "hardBreak"})
        out += inline(ln, names)
    return out


def build_adf(md, names, images=None):
    """images(path) -> (uuid, width, height); only called for `![cap](path)` lines."""
    blocks = []
    # an image line always ends its own paragraph, so it can sit anywhere in the text
    md = re.sub(r"^(!\[[^\]]*\]\([^)\s][^)]*\))[ \t]*$", r"\n\n\1\n\n", md.strip(), flags=re.M)
    for chunk in re.split(r"\n\s*\n", md.strip()):
        ls = chunk.split("\n")
        im = IMG_LINE.fullmatch(chunk.strip())
        if im:
            if images is None:
                die(2, f"image {im.group('path')!r} found but no image resolver")
            blocks += image_blocks(im.group("cap"), images(im.group("path")))
            continue
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


def png_size(path):
    with open(path, "rb") as f:
        h = f.read(24)
    if h[:8] == b"\x89PNG\r\n\x1a\n" and h[12:16] == b"IHDR":
        return struct.unpack(">II", h[16:24])
    return 1280, 800  # not a PNG: size only affects display scaling


def auth_header():
    e = env()
    return "Basic " + base64.b64encode(f"{e['JIRA_EMAIL']}:{e['JIRA_API_TOKEN']}".encode()).decode()


def multipart(path):
    boundary = uuid.uuid4().hex
    name = os.path.basename(path).replace('"', "")
    with open(path, "rb") as f:
        data = f.read()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, "multipart/form-data; boundary=" + boundary


def upload_attachment(ticket, path):
    body, ctype = multipart(path)
    req = urllib.request.Request(
        env()["JIRA_URL"] + f"/rest/api/3/issue/{ticket}/attachments", method="POST", data=body,
        headers={"Authorization": auth_header(), "X-Atlassian-Token": "no-check", "Content-Type": ctype, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            att = json.loads(r.read())
    except urllib.error.HTTPError as ex:
        die(4, f"upload {path} -> HTTP {ex.code}: {ex.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as ex:
        die(4, f"upload {path} failed: {ex.reason}")
    if not att or not att[0].get("id"):
        die(4, f"upload {path}: no attachment id in response")
    return att[0]["id"]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def media_uuid(att_id):
    """The attachment content endpoint 30x-redirects to the media service; the file UUID is in Location."""
    req = urllib.request.Request(env()["JIRA_URL"] + f"/rest/api/3/attachment/content/{att_id}",
                                 headers={"Authorization": auth_header()})
    try:
        urllib.request.build_opener(_NoRedirect).open(req, timeout=30)
    except urllib.error.HTTPError as ex:
        loc = ex.headers.get("Location", "")
        m = ex.code in (301, 302, 303, 307, 308) and UUID_RE.search(loc)
        if m:
            return m.group(0)
        die(4, f"attachment {att_id}: HTTP {ex.code}, no media UUID in redirect")
    except urllib.error.URLError as ex:
        die(4, f"attachment {att_id} lookup failed: {ex.reason}")
    die(4, f"attachment {att_id}: expected a redirect to the media service, got none")


def make_resolver(ticket, dry):
    seen = {}

    def resolve(path):
        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            die(2, f"image not found: {path}")
        if path not in seen:
            if dry:
                print(f"[dry-run] would upload {path} to {ticket}", file=sys.stderr)
                seen[path] = ("<uuid-after-upload>", *png_size(path))
            else:
                seen[path] = (media_uuid(upload_attachment(ticket, path)), *png_size(path))
        return seen[path]
    return resolve


def split_image_opts(args):
    """-> (args without --image, ['![cap](path)' lines])"""
    rest, extra, i = [], [], 0
    while i < len(args):
        if args[i] == "--image":
            if i + 1 >= len(args):
                die(2, "--image needs PATH[:CAPTION]")
            path, _, cap = args[i + 1].partition(":")
            extra.append(f"![{cap}]({path})")
            i += 2
        else:
            rest.append(args[i])
            i += 1
    return rest, extra


def read_body(src):
    try:
        md = sys.stdin.read() if src is None else open(src).read()
    except OSError as ex:
        die(2, f"cannot read {src}: {ex}")
    return md


def check_ticket(t):
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", t):
        die(2, f"bad ticket id: {t!r}")


def src_of(args, usage):
    if args == ["-"]:
        return None
    if len(args) == 2 and args[0] == "--file":
        return args[1]
    die(2, usage)


def cmd_post(args):
    usage = "usage: post <TICKET> (--file PATH | -) [--image PATH[:CAPTION]]... [--dry-run]"
    dry = "--dry-run" in args
    args, extra = split_image_opts([a for a in args if a != "--dry-run"])
    if not args:
        die(2, usage)
    src = src_of(args[1:], usage)
    check_ticket(args[0])
    md = read_body(src)
    if not md.strip():
        die(2, "empty comment body")
    adf = build_adf("\n\n".join([md] + extra), (lambda i: i) if dry else display_name, make_resolver(args[0], dry))
    if dry:
        print(json.dumps(adf, indent=2, ensure_ascii=False))
        return
    want = list(mention_ids(adf))
    res = call("POST", f"/rest/api/3/issue/{args[0]}/comment", {"body": adf})
    report(args[0], res, want)


def cmd_edit(args):
    usage = "usage: edit <TICKET> <COMMENT_ID> (--file PATH | -) [--image PATH[:CAPTION]]... [--dry-run]"
    dry = "--dry-run" in args
    args, extra = split_image_opts([a for a in args if a != "--dry-run"])
    if len(args) < 2 or not args[1].isdigit():
        die(2, usage)
    src = src_of(args[2:], usage)
    check_ticket(args[0])
    md = read_body(src)
    if not md.strip():
        die(2, "empty comment body")
    adf = build_adf("\n\n".join([md] + extra), (lambda i: i) if dry else display_name, make_resolver(args[0], dry))
    if dry:
        print(json.dumps(adf, indent=2, ensure_ascii=False))
        return
    want = list(mention_ids(adf))
    res = call("PUT", f"/rest/api/3/issue/{args[0]}/comment/{args[1]}?notifyUsers=false", {"body": adf})
    report(args[0], res, want)


def report(ticket, res, want):
    got = set(mention_ids(res.get("body")))
    cid = res.get("id")
    print(json.dumps({"id": cid, "url": f"{env()['JIRA_URL']}/browse/{ticket}?focusedCommentId={cid}", "mentions": sorted(got)}))
    missing = [i for i in want if i not in got]
    if missing:
        die(5, f"comment {cid} saved but mention(s) did not come back as mention nodes: {', '.join(missing)}")


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
    d = build_adf("Before\n![Shot one](/x/a.png)\nAfter @[Ann](a:1)\n\n![](/x/b.png)",
                  lambda i: i, lambda p: ("uuid-" + p[-5:], 640, 480))
    t = [b["type"] for b in d["content"]]
    assert t == ["paragraph", "paragraph", "mediaSingle", "paragraph", "mediaSingle"], t
    assert d["content"][1]["content"][0]["marks"] == [{"type": "em"}]  # caption
    m = d["content"][2]["content"][0]["attrs"]
    assert m == {"type": "file", "id": "uuid-a.png", "collection": "", "width": 640, "height": 480}, m
    assert d["content"][2]["attrs"] == {"layout": "center"}
    assert list(mention_ids(d)) == ["a:1"]
    assert split_image_opts(["T", "--image", "/p/a.png:Cap", "--image", "/p/b.png"]) == (["T"], ["![Cap](/p/a.png)", "![](/p/b.png)"])
    assert UUID_RE.search("https://api.media/file/0a1b2c3d-1111-2222-3333-444455556666/binary?x=1")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        f.write(b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR" + struct.pack(">II", 300, 200))
        f.flush()
        assert png_size(f.name) == (300, 200)
    print("self-test ok")


def main():
    a = sys.argv[1:]
    if a == ["--self-test"]:
        return self_test()
    if a and a[0] == "post":
        return cmd_post(a[1:])
    if a and a[0] == "edit":
        return cmd_edit(a[1:])
    if a and a[0] == "delete":
        return cmd_delete(a[1:])
    die(2, __doc__)


if __name__ == "__main__":
    main()
