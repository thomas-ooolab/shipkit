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
    else
      echo "node package.json"
    fi
  elif [ -f "$dir/go.mod" ]; then echo "go go.mod"
  elif [ -f "$dir/pyproject.toml" ]; then echo "python pyproject.toml"
  elif [ -f "$dir/requirements.txt" ]; then echo "python requirements.txt"
  elif [ -f "$dir/setup.py" ]; then echo "python setup.py"
  elif [ -f "$dir/Cargo.toml" ]; then echo "rust Cargo.toml"
  elif [ -f "$dir/pom.xml" ]; then echo "java pom.xml"
  elif [ -f "$dir/build.gradle" ] || [ -f "$dir/build.gradle.kts" ]; then echo "java gradle"
  elif [ -f "$dir/Gemfile" ]; then echo "ruby Gemfile"
  else echo "unknown -"
  fi
}

case "${1:-}" in
  topology)
    if [ -f .gitmodules ]; then
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
    if [ -d specs ]; then
      echo "SPEC_DIR=specs"
      last=$(ls specs 2>/dev/null | grep -E '^[0-9]+' | sort | tail -1)
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
    # Config-first resolution for run-pipeline. Requires bootstrap.
    if [ -f .shipkit/config.yml ]; then
      echo "SHIPKIT_CONFIG_EXISTS=1"
      echo "----- .shipkit/config.yml -----"
      cat .shipkit/config.yml
      echo "----- end -----"
      # also surface next spec number from disk (ground truth beats the cached value)
      last=$(ls "$(grep -E '^\s*dir:' .shipkit/config.yml | head -1 | awk '{print $2}' || echo specs)" 2>/dev/null | grep -E '^[0-9]+' | sort | tail -1)
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
    # spec: match frontmatter `ticket:` first, then a dir name containing the ticket
    specfile=$(grep -rl "ticket:[[:space:]]*$ticket" specs/*/spec.md 2>/dev/null | head -1)
    if [ -n "$specfile" ]; then echo "SPEC=$(dirname "$specfile")"; else
      d=$(ls -d specs/*"$ticket"* 2>/dev/null | head -1); echo "SPEC=${d:-none}"; fi
    echo "BRANCHES:"
    bp=$(git branch --list "feat/$ticket-*" 2>/dev/null | sed 's/^[* ]*//' | head -1)
    echo "- parent: branch=${bp:-none}"
    if [ -f .gitmodules ]; then
      paths=$(git config -f .gitmodules --get-regexp '\.path$' 2>/dev/null | awk '{print $2}')
      while IFS= read -r p; do
        [ -z "$p" ] && continue
        b=$(git -C "$p" branch --list "feat/$ticket-*" 2>/dev/null | sed 's/^[* ]*//' | head -1)
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

  *)
    echo "usage: probe.sh {topology|remote|spec|config|context|resolve|state <ticket>}" >&2
    exit 2
    ;;
esac
