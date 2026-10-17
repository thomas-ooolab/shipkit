#!/usr/bin/env bash
# shipkit probe — evidence-first detection for /bootstrap.
# Emits KEY=VALUE / structured blocks the command reads. Never guesses; only
# reports what is actually present on disk. Read-only. Usage: probe.sh <subcommand>
set -uo pipefail

# Detect the stack of a directory from manifest files actually present.
# Echoes: "<stack> <manifest>" or "unknown -".
detect_stack() {
  local dir="$1"
  if [ -f "$dir/package.json" ]; then
    if grep -qE '"(next)"[[:space:]]*:' "$dir/package.json" 2>/dev/null; then
      echo "nextjs package.json"
    elif grep -qE '"(react|react-native|vue|svelte|@angular/core|vite)"[[:space:]]*:' "$dir/package.json" 2>/dev/null; then
      echo "react package.json"
    else
      echo "node package.json"
    fi
  elif [ -f "$dir/go.mod" ]; then echo "go go.mod"
  elif [ -f "$dir/pubspec.yaml" ]; then echo "flutter pubspec.yaml"
  elif [ -f "$dir/pyproject.toml" ]; then echo "python pyproject.toml"
  elif [ -f "$dir/requirements.txt" ]; then echo "python requirements.txt"
  elif [ -f "$dir/setup.py" ]; then echo "python setup.py"
  elif [ -f "$dir/manage.py" ]; then echo "python manage.py"
  elif [ -f "$dir/gunicorn.conf.py" ]; then echo "python gunicorn.conf.py"
  elif [ -f "$dir/composer.json" ]; then echo "php composer.json"
  elif [ -f "$dir/Cargo.toml" ]; then echo "rust Cargo.toml"
  elif [ -f "$dir/pom.xml" ]; then echo "java pom.xml"
  elif [ -f "$dir/build.gradle" ] || [ -f "$dir/build.gradle.kts" ]; then echo "java gradle"
  elif [ -f "$dir/Gemfile" ]; then echo "ruby Gemfile"
  else echo "unknown -"
  fi
}

# The project root, wherever the shell stands (a spec dir, a submodule): the nearest ancestor with
# .shipkit/config.yml. Before bootstrap there is none — then the outermost git root, since
# `git rev-parse --show-toplevel` inside a submodule returns the submodule, not the meta repo.
find_root() {
  local d sp
  d=$(pwd -P)
  while [ "$d" != "/" ]; do
    [ -f "$d/.shipkit/config.yml" ] && { echo "$d"; return; }
    d=$(dirname "$d")
  done
  d=$(git rev-parse --show-toplevel 2>/dev/null) || { pwd -P; return; }
  while sp=$(git -C "$d" rev-parse --show-superproject-working-tree 2>/dev/null) && [ -n "$sp" ]; do d="$sp"; done
  echo "$d"
}
# The spec dir from .shipkit/config.yml (`spec: { dir: specs, ... }` or a block `dir:` under `spec:`), else `specs`.
spec_dir() {
  local d=""
  [ -f .shipkit/config.yml ] && d=$(sed -n -E 's/^[[:space:]]*spec:.*[{,][[:space:]]*dir:[[:space:]]*"?([^,}" ]+).*/\1/p; s/^[[:space:]]+dir:[[:space:]]*"?([^,}" ]+).*/\1/p' .shipkit/config.yml | head -1)
  echo "${d:-specs}"
}
# The ticket's spec dir (`specs/NNN-slug`) or `none`: frontmatter `ticket:` (or `jira:`, older specs)
# first, then a dir name containing the ticket.
find_spec() {
  local f d
  local sd; sd=$(spec_dir)
  f=$(grep -rlE "^(ticket|jira):[[:space:]]*\"?$1\"?[[:space:]]*$" "$sd"/*/spec.md 2>/dev/null | head -1)
  if [ -n "$f" ]; then dirname "$f"; return; fi
  d=$(ls -d "$sd"/*"$1"* 2>/dev/null | head -1); echo "${d:-none}"
}
START=$(pwd -P)
ROOT=$(find_root)
if [ "$ROOT" != "$START" ]; then
  cd "$ROOT" || exit 1
  # every path below is relative to ROOT — the caller must not read them against its own cwd
  echo "SHIPKIT_ROOT_MOVED=from $START to $ROOT (paths below are relative to $ROOT; cd there before using them)"
fi

case "${1:-}" in
  topology)
    if [ -f .gitmodules ]; then
      echo "TOPOLOGY_MODE=meta-with-submodules"
      echo "GITMODULES_EXISTS=1"
      # Pair up submodule path + branch from .gitmodules
      paths=$(git config -f .gitmodules --get-regexp '\.path$' 2>/dev/null | awk '{print $2}')
      count=0
      echo "SUBMODULES:"
      while IFS= read -r p; do
        [ -z "$p" ] && continue
        name=$(git config -f .gitmodules --get-regexp "\.path$" 2>/dev/null | grep " $p$" | sed -E 's/^submodule\.(.*)\.path .*/\1/')
        branch=$(git config -f .gitmodules --get "submodule.$name.branch" 2>/dev/null)
        [ -z "$branch" ] && branch="(unset — defaults to main)"
        read -r stack manifest <<<"$(detect_stack "$p")"
        echo "- path=$p branch=$branch stack=$stack manifest=$manifest"
        count=$((count+1))
      done <<<"$paths"
      echo "SUBMODULE_COUNT=$count"
    else
      echo "TOPOLOGY_MODE=single-repo"
      echo "GITMODULES_EXISTS=0"
      read -r stack manifest <<<"$(detect_stack ".")"
      echo "ROOT_STACK=$stack ROOT_MANIFEST=$manifest"
    fi
    ;;

  remote)
    url=$(git remote get-url origin 2>/dev/null)
    if [ -z "$url" ]; then echo "REMOTE=none"; exit 0; fi
    echo "REMOTE_URL=$url"
    host=$(echo "$url" | sed -E 's#(git@|https://)([^:/]+).*#\2#')
    echo "REMOTE_HOST=$host"
    # workspace/owner = first path segment after host
    ws=$(echo "$url" | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#')
    echo "REMOTE_WORKSPACE=$ws"
    ;;

  spec)
    sd=$(spec_dir)
    if [ -d "$sd" ]; then
      echo "SPEC_DIR=$sd"
      last=$(ls "$sd" 2>/dev/null | grep -E '^[0-9]+' | sort | tail -1)
      if [ -n "$last" ]; then
        num=$(echo "$last" | grep -oE '^[0-9]+')
        pad=${#num}
        next=$(printf "%0${pad}d" "$((10#$num + 1))")
        echo "HIGHEST_SPEC=$last NEXT_SPEC=$next ZERO_PAD=$pad"
      else
        echo "HIGHEST_SPEC=none NEXT_SPEC=001 ZERO_PAD=3"
      fi
    else
      echo "SPEC_DIR=none NEXT_SPEC=001 ZERO_PAD=3"
    fi
    ;;

  config)
    if [ -f .shipkit/config.yml ]; then
      echo "SHIPKIT_CONFIG_EXISTS=1"
      echo "----- .shipkit/config.yml -----"
      cat .shipkit/config.yml
      echo "----- end -----"
    else
      echo "SHIPKIT_CONFIG_EXISTS=0"
    fi
    ;;

  context)
    [ -f CLAUDE.md ] && echo "ROOT_CLAUDE_MD=present" || echo "ROOT_CLAUDE_MD=absent"
    [ -f .claude/CLAUDE.md ] && echo "DOT_CLAUDE_MD=present" || echo "DOT_CLAUDE_MD=absent"
    [ -d docs/features ] && echo "FEATURES_INDEX=$( [ -f docs/features/INDEX.md ] && echo present || echo absent )" || echo "FEATURES_INDEX=absent"
    ;;

  resolve)
    echo "SHIPKIT_ROOT=$ROOT"
    # Topology auto-detect (independent of config, so skills branch correctly even pre-bootstrap).
    if [ -f .gitmodules ]; then echo "TOPOLOGY_MODE=meta-with-submodules"; else echo "TOPOLOGY_MODE=single-repo"; fi
    # Config-first resolution for run-pipeline. Requires bootstrap.
    if [ -f .shipkit/config.yml ]; then
      echo "SHIPKIT_CONFIG_EXISTS=1"
      echo "----- .shipkit/config.yml -----"
      cat .shipkit/config.yml
      echo "----- end -----"
      # also surface next spec number from disk (ground truth beats the cached value)
      last=$(ls "$(spec_dir)" 2>/dev/null | grep -E '^[0-9]+' | sort | tail -1)
      [ -n "$last" ] && echo "DISK_HIGHEST_SPEC=$last"
    else
      echo "SHIPKIT_CONFIG_EXISTS=0"
      echo "Run /bootstrap first."
    fi
    ;;

  state)
    # Local ground truth for one ticket. Usage: probe.sh state <TICKET>
    ticket="${2:-}"
    if [ -z "$ticket" ]; then echo "STATE_ERROR=no-ticket" >&2; exit 2; fi
    echo "TICKET=$ticket"
    if [ -f .gitmodules ]; then echo "TOPOLOGY_MODE=meta-with-submodules"; else echo "TOPOLOGY_MODE=single-repo"; fi
    echo "SPEC=$(find_spec "$ticket")"
    echo "BRANCHES:"
    bp=$(git branch --list "feat/$ticket-*" "fix/$ticket-*" 2>/dev/null | sed 's/^[* ]*//' | head -1)
    if [ -f .gitmodules ]; then
      echo "- parent: branch=${bp:-none}"
    else
      # single-repo: the repo itself carries the feature branch + changes
      if [ -n "$bp" ]; then
        dirty=$(git status --porcelain 2>/dev/null | head -1)
        ahead=$(git rev-list --count "@{upstream}..$bp" 2>/dev/null || echo "?")
        echo "- repo: branch=$bp dirty=$([ -n "$dirty" ] && echo yes || echo no) unpushed=$ahead"
      else
        echo "- repo: branch=none"
      fi
    fi
    if [ -f .gitmodules ]; then
      paths=$(git config -f .gitmodules --get-regexp '\.path$' 2>/dev/null | awk '{print $2}')
      while IFS= read -r p; do
        [ -z "$p" ] && continue
        # not checked out: `git -C` would fall through to the parent repo and report ITS branch
        if [ ! -e "$p/.git" ]; then echo "- $p: branch=none (not checked out)"; continue; fi
        b=$(git -C "$p" branch --list "feat/$ticket-*" "fix/$ticket-*" 2>/dev/null | sed 's/^[* ]*//' | head -1)
        if [ -n "$b" ]; then
          dirty=$(git -C "$p" status --porcelain 2>/dev/null | head -1)
          ahead=$(git -C "$p" rev-list --count "@{upstream}..$b" 2>/dev/null || echo "?")
          echo "- $p: branch=$b dirty=$([ -n "$dirty" ] && echo yes || echo no) unpushed=$ahead"
        else
          echo "- $p: branch=none"
        fi
      done <<<"$paths"
    fi
    ;;

  branch)
    # The one place the branch convention lives: feat/<TICKET>-<slug><suffix> (a bug fix on a new worktree: fix/…, --fix).
    # Usage: probe.sh branch <TICKET> [<submodule name>|parent] [--fix]   (parent / single-repo: no suffix)
    ticket="${2:-}"; target="${3:-parent}"; kind=feat
    if [ "$target" = --fix ]; then target=parent; fi
    if [ "${4:-}" = --fix ] || [ "${3:-}" = --fix ]; then kind=fix; fi
    if [ -z "$ticket" ]; then echo "BRANCH_ERROR=no-ticket" >&2; exit 2; fi
    spec=$(find_spec "$ticket")
    if [ "$spec" = none ]; then
      echo "BRANCH=none"
      echo "BRANCH_NOTE=no spec for $ticket — slug = the ticket title in kebab-case (<=5 words), then $kind/$ticket-<slug><suffix>"
      exit 0
    fi
    slug=$(basename "$spec" | sed -E 's/^[0-9]+-//')
    suffix=""
    if [ "$target" != parent ] && [ -f .shipkit/config.yml ]; then
      suffix=$(grep -E "name:[[:space:]]*$target[,[:space:]}]" .shipkit/config.yml | sed -n 's/.*suffix:[[:space:]]*\([^, }]*\).*/\1/p' | head -1)
    fi
    echo "BRANCH=$kind/$ticket-$slug$suffix"
    ;;

  *)
    echo "usage: probe.sh {topology|remote|spec|config|context|resolve|state <ticket>|branch <ticket> [<submodule>] [--fix]}" >&2
    exit 2
    ;;
esac
