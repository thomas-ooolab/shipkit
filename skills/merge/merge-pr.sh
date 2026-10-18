#!/usr/bin/env bash
# merge-pr.sh — merge ONE Bitbucket PR and print one line: `<repo> #<id> MERGED <full merge sha>`.
# The response goes to a temp FILE and is judged by merge-pr.py: never echoed through the shell (zsh's echo
# turns the backslash-n in a JSON error into a real control character and breaks the parse), and the exit
# status is this script's own, so a caller never has to read it through a pipe.
#
#   usage: merge-pr.sh <workspace> <repo> <pr_id>        (run with `bash`)
#   env:   BITBUCKET_USERNAME  BITBUCKET_APP_PASSWORD     (required; BITBUCKET_API_TOKEN is read when the second is empty)   POLL_S (default 3)  POLL_MAX (default 40)
#
# No merge strategy is sent: the repo's own Bitbucket default applies. An async merge (HTTP 202) is followed
# through its Location task URL until it finishes.
#
# exit 0  merged — the line is on stdout
# exit 1  Bitbucket refused, or the state is not MERGED — `ERROR ...` with the verbatim message on stderr
# exit 3  curl failed (network/DNS) or the async merge did not finish in POLL_MAX polls
# exit 4  bad usage or credentials not set
set -u

if [ "$#" -ne 3 ]; then
  echo "usage: merge-pr.sh <workspace> <repo> <pr_id>" >&2
  exit 4
fi
# an API token is the credential Bitbucket issues now; the variable keeps its old name, so BITBUCKET_API_TOKEN stands in when it is empty
BITBUCKET_APP_PASSWORD="${BITBUCKET_APP_PASSWORD:-${BITBUCKET_API_TOKEN:-}}"
if [ -z "${BITBUCKET_USERNAME:-}" ] || [ -z "${BITBUCKET_APP_PASSWORD:-}" ]; then
  echo "BITBUCKET_USERNAME / BITBUCKET_APP_PASSWORD (or BITBUCKET_API_TOKEN) not set" >&2
  exit 4
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$1"; REPO="$2"; PR="$3"
POLL_S="${POLL_S:-3}"; POLL_MAX="${POLL_MAX:-40}"
URL="https://api.bitbucket.org/2.0/repositories/${WORKSPACE}/${REPO}/pullrequests/${PR}/merge"

body_file=$(mktemp); head_file=$(mktemp)
trap 'rm -f "$body_file" "$head_file"' EXIT

# credentials go to curl on stdin (a curl config), not onto its command line
cred="${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}"; cred="${cred//\\/\\\\}"; cred="${cred//\"/\\\"}"
call() { # <curl args...> -> prints the HTTP code; body in $body_file, headers in $head_file
  printf 'user = "%s"\n' "$cred" | curl -sS -K - -o "$body_file" -D "$head_file" -w '%{http_code}' "$@"
}

code=$(call -X POST -H 'Content-Type: application/json' -d '{}' "$URL") || { echo "ERROR ${REPO} #${PR}: curl failed" >&2; exit 3; }

n=0
while :; do
  python3 "$HERE/merge-pr.py" "$REPO" "$PR" "$code" "$body_file"
  rc=$?
  [ "$rc" -ne 10 ] && exit "$rc"
  n=$((n + 1))
  if [ "$n" -gt "$POLL_MAX" ]; then
    echo "ERROR ${REPO} #${PR}: merge still running after $((POLL_MAX * POLL_S))s" >&2
    exit 3
  fi
  task_url=$(awk 'tolower($1) == "location:" { sub(/\r$/, "", $2); print $2; exit }' "$head_file")
  [ -z "$task_url" ] && task_url="$URL"
  sleep "$POLL_S"
  code=$(call "$task_url") || { echo "ERROR ${REPO} #${PR}: curl failed while polling" >&2; exit 3; }
done
