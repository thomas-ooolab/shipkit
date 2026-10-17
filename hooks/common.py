"""Helpers shared by the hooks: shell-command parsing and the weekend clock (loaded by file path — `python3 -I` does not
put this folder on sys.path)."""
import datetime, os, re, shlex

SHELLS = {"bash", "sh", "zsh"}

def words_of(seg):
    """shlex words of one segment without its leading VAR=value assignments."""
    try:
        words = shlex.split(seg)
    except ValueError:
        words = seg.split()
    while words and re.fullmatch(r"[A-Za-z_]\w*=\S*", words[0]):
        words = words[1:]
    return words

def segments(command, runners):
    """Segments of `command` (split on ; && || | newline) whose first word is in `runners`, as shlex word lists, in order.
    A heredoc body is text, not commands (`cat <<'EOF' … EOF`): it is dropped, the line that opens it is kept.
    `bash -c '…'` is searched one level down."""
    command = re.sub(r"(<<-?\s*[\x22']?(\w+)[\x22']?[^\n]*\n).*?\n[ \t]*\2[ \t]*(?=\n|$)", r"\1", command, flags=re.S)
    out = []
    for seg in re.split(r"&&|\|\||[;|\n]", command):
        seg = seg.strip()
        if not seg:
            continue
        words = words_of(seg)
        if not words or os.path.basename(words[0]) not in runners:
            continue
        out.append((seg, words))
        if len(words) >= 3 and words[1] in ("-c", "-lc") and os.path.basename(words[0]) in SHELLS:
            out += segments(words[2], runners)
    return out

def now_in(env):
    """The current time in $SHIPKIT_TZ (an IANA zone), else the machine's local time."""
    tz = env.get("SHIPKIT_TZ")
    if tz:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(tz))
    return datetime.datetime.now()

def is_weekend(now):
    return now.weekday() >= 5
