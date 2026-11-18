#!/usr/bin/env bash
# Runs the plugin's eval suite (evals/) with the flags its cases need: --scaffold builds each rule/issue case's fixture workspace
# and the one Bash grant lets the skills' `!` injection run probe.sh. Every run is a model call (a 61-case run, 3 runs each, costs
# tens of dollars): pass --tag, --case or --runs to run less. Extra arguments go to `claude plugin eval` as they are.
#   usage: bash scripts/run-evals.sh [--tag routing|rules|issues] [--case <glob>] [--runs <n>] [--ablation none|with-without]
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT" || exit 1
exec claude plugin eval . --trust-plugin --no-publish -j 6 --scaffold --allow-tools 'Bash(bash *probe.sh*)' --ablation none "$@"
