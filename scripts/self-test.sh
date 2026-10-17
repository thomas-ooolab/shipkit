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
run "hooks.json is valid JSON"          python3 -I -c "import json; json.load(open('hooks/hooks.json'))"
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
for f in scripts/*.sh skills/*/*.sh .githooks/pre-commit; do run "bash -n $f" bash -n "$f"; done
exit "$fail"
