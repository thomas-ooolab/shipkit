#!/usr/bin/env bash
# Runs every self-check the plugin ships: the pipeline-drift check, each script's --self-test, the verdict-predicate
# tests, and `bash -n` on every shell script. Exit 0 = all pass. The pre-commit hook runs this.
#   usage: bash scripts/self-test.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT" || exit 1
fail=0
run() { # <label> <cmd...>
  local label="$1"; shift
  if out=$("$@" 2>&1); then echo "ok    $label"; else echo "FAIL  $label"; echo "$out" | sed 's/^/        /' | tail -15; fail=1; fi
}
run "check-pipeline (drift + versions)" python3 -I scripts/check-pipeline.py
run "check-pipeline --self-test"        python3 -I scripts/check-pipeline.py --self-test
run "check-skills (frontmatter, refs)"  python3 -I scripts/check-skills.py
run "check-skills --self-test"          python3 -I scripts/check-skills.py --self-test
run "weekend-guard hook"                python3 -I hooks/weekend-guard.py --self-test
run "pr-branch-guard hook"               python3 -I hooks/pr-branch-guard.py --self-test
run "after-hours-push-guard hook"       python3 -I hooks/after-hours-push-guard.py --self-test
run "hooks.json is valid JSON"         python3 -I -c "import json; json.load(open('hooks/hooks.json'))"
run "jira-comment.py"                   python3 -I scripts/jira-comment.py --self-test
run "merge-pr.py"                       python3 -I skills/merge/merge-pr.py --self-test
run "pipelines-status.py"               python3 -I skills/merge/pipelines-status.py --self-test
run "verdict-predicate tests"           python3 -I skills/pr/test-verdict-predicate.py
if command -v node >/dev/null 2>&1; then
  run "post-slack.js"                   node scripts/post-slack.js --self-test
  run "wait-for-slack-event.js"         node scripts/wait-for-slack-event.js --self-test
  run "observe-slack.js"                node skills/developer/observe-slack.js --self-test
else
  echo "skip  node scripts (node not installed)"
fi
screen_of() { # <screen line>... -> the SCREEN= verdict wait-for-agent.sh gives a canned terminal tail (a stub orca prints it)
  local stub; stub=$(mktemp)
  { echo '#!/usr/bin/env bash'; echo "cat <<'J'"
    python3 -I -c 'import json,sys; print(json.dumps({"ok": True, "result": {"terminal": {"status": "running", "tail": sys.argv[1:]}}}))' "$@"
    echo J; } >"$stub"
  chmod +x "$stub"; ORCA_CLI_COMMAND="$stub" bash scripts/wait-for-agent.sh h --once | head -1; rm -f "$stub"
}
rule='────────────────────────'; trust='Trust All Tools active, confirmations are off · /quit to exit'
run "wait-for-agent.sh: usage limit"   test "$(screen_of "• You've reached your monthly usage limit. Please return next month to continue building. (Request ID: x)" "▸ Credits: turn 1" "$rule" "$trust" "$rule")" = SCREEN=limit
run "wait-for-agent.sh: idle box"      test "$(screen_of "• Write file:///x" "$rule" "$trust" "$rule")" = SCREEN=agent
run "cleanup-browsers.sh"              bash scripts/test-cleanup-browsers.sh
for f in scripts/*.sh skills/*/*.sh .githooks/pre-commit; do run "bash -n $f" bash -n "$f"; done
exit "$fail"
