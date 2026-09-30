#!/usr/bin/env bash
# wait-pipelines.sh — block until the Bitbucket pipeline triggered by each merge commit is COMPLETED.
#
#   usage: bash wait-pipelines.sh <workspace> <branch> <repo>=<merge_sha> [<repo>=<merge_sha> ...]
#   env:   INTERVAL (seconds between polls, default 20)  TIMEOUT_MIN (default 40)  FAIL_LIMIT (default 5)
#
# Each poll runs `twg bitbucket pipeline query` once per repo and hands the JSON to
# pipelines-status.py, which matches the run by target.commit.hash == merge sha (never "latest run").
# Run with `bash`, not `zsh`/bare (zsh doesn't word-split); there is no `timeout` on macOS, so the
# deadline is tracked here.
#
# exit 0  every repo's run is COMPLETED (a FAILED/STOPPED/ERROR result is still exit 0 — read the table)
# exit 2  timed out
# exit 3  twg failed FAIL_LIMIT polls in a row
# exit 4  bad usage
set -u

if [ "$#" -lt 3 ]; then
  echo "usage: wait-pipelines.sh <workspace> <branch> <repo>=<merge_sha> ..." >&2
  exit 4
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$1"; BRANCH="$2"; shift 2
INTERVAL="${INTERVAL:-20}"; TIMEOUT_MIN="${TIMEOUT_MIN:-40}"; FAIL_LIMIT="${FAIL_LIMIT:-5}"

for t in "$@"; do
  case "$t" in *=*) ;; *) echo "bad target '$t' — expected <repo>=<merge_sha>" >&2; exit 4 ;; esac
done

deadline=$((SECONDS + TIMEOUT_MIN * 60))
fails=0

while :; do
  rows=""; pending=0; failed_repo=""
  for t in "$@"; do
    repo="${t%%=*}"; sha="${t#*=}"
    if ! json=$(twg bitbucket pipeline query --workspace "$WORKSPACE" --repo "$repo" --branch "$BRANCH" \
                  --limit 6 -o json --output-summary none 2>/dev/null); then
      failed_repo="$repo"; break
    fi
    row=$(printf '%s' "$json" | python3 "$HERE/pipelines-status.py" "$repo" "$sha") || { failed_repo="$repo"; break; }
    rows="${rows}${row}"$'\n'
    case "$row" in *"|COMPLETED|"*) ;; *) pending=$((pending + 1)) ;; esac
  done

  if [ -n "$failed_repo" ]; then
    fails=$((fails + 1))
    echo "twg/parse failed for ${failed_repo} (${fails}/${FAIL_LIMIT})" >&2
    [ "$fails" -ge "$FAIL_LIMIT" ] && exit 3
  else
    fails=0
    if [ "$pending" -eq 0 ]; then
      printf 'repo|run#|sha|state|result\n%s' "$rows" | column -s'|' -t
      exit 0
    fi
  fi

  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "TIMEOUT after ${TIMEOUT_MIN}m — last status:" >&2
    printf 'repo|run#|sha|state|result\n%s' "$rows" | column -s'|' -t >&2
    exit 2
  fi
  sleep "$INTERVAL"
done
