#!/usr/bin/env bash
# bitbucket-api.sh — ONE Bitbucket Cloud REST call, the shared helper for every skill that talks to the API
# (/pr, /review-changes, /bump-submodule, /run-pipeline, /spec-from-ticket). /merge keeps its own merge-pr.sh.
#
#   usage: bash bitbucket-api.sh <GET|POST|PUT|DELETE> <path-under-2.0 | https://api.bitbucket.org/... url> [<json body file>]
#   e.g.   bash bitbucket-api.sh GET "/repositories/<workspace>/<repo>/pullrequests?q=source.branch.name%3D%22feat/AR-1-x%22&state=OPEN"
#          bash bitbucket-api.sh POST "/repositories/<workspace>/<repo>/pullrequests" body.json
#   env:   BITBUCKET_USERNAME  BITBUCKET_APP_PASSWORD   (required)
#          The variable keeps its old name, but it may hold an API token: Bitbucket accepts either as the Basic-auth
#          password. With an API token, BITBUCKET_USERNAME is the Atlassian account e-mail.
#
# stdout: the response body, only on success. Credentials go to curl on stdin (a curl config), never onto its
# command line; the body goes through a file, never through `echo` (zsh turns a JSON backslash-n into a newline).
# exit 0  HTTP 2xx            exit 1  any other HTTP status — `ERROR HTTP <code>: <message>` on stderr
# exit 3  curl failed (network/DNS)                    exit 4  bad usage or credentials not set
set -u

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: bitbucket-api.sh <GET|POST|PUT|DELETE> <path|url> [<json body file>]" >&2; exit 4
fi
if [ -z "${BITBUCKET_USERNAME:-}" ] || [ -z "${BITBUCKET_APP_PASSWORD:-}" ]; then
  echo "BITBUCKET_USERNAME / BITBUCKET_APP_PASSWORD not set (the second may be an API token; then the first is your Atlassian e-mail)" >&2; exit 4
fi
METHOD="$1"; TARGET="$2"; BODY="${3:-}"
case "$TARGET" in
  https://api.bitbucket.org/*) URL="$TARGET" ;;
  /*) URL="https://api.bitbucket.org/2.0${TARGET}" ;;
  *) echo "path must start with / or be an https://api.bitbucket.org/ url" >&2; exit 4 ;;
esac
if [ -n "$BODY" ] && [ ! -f "$BODY" ]; then echo "body file not found: $BODY" >&2; exit 4; fi

out=$(mktemp); trap 'rm -f "$out"' EXIT
cred="${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}"; cred="${cred//\\/\\\\}"; cred="${cred//\"/\\\"}"
args=(-sS -K - -X "$METHOD" -H "Accept: application/json" -o "$out" -w '%{http_code}')
[ -n "$BODY" ] && args+=(-H "Content-Type: application/json" --data-binary "@$BODY")
code=$(printf 'user = "%s"\n' "$cred" | curl "${args[@]}" "$URL") || { echo "ERROR: curl failed for $METHOD $URL" >&2; exit 3; }

case "$code" in
  2??) cat "$out"; exit 0 ;;
  *) msg=$(python3 -I -c 'import json,sys
try: d=json.load(open(sys.argv[1])); print((d.get("error") or {}).get("message") or str(d)[:300])
except Exception: print(open(sys.argv[1],errors="replace").read()[:300].strip())' "$out" 2>/dev/null)
     echo "ERROR HTTP $code: $msg" >&2; exit 1 ;;
esac
