#!/usr/bin/env bash
# shipkit recon helper — evidence-first support for /design-recon and /design-verify.
#
# Read-only except `serve` (starts a transient local static server so an HTML mockup
# with relative asset paths loads reliably; `file://` is tried first by the skill).
# Never guesses; only reports what is actually on disk. Usage: recon.sh <subcommand>
set -uo pipefail

case "${1:-}" in
  # classify <path-or-url> — what kind of design artifact is this?
  # Emits ARTIFACT_TYPE=url|html|screenshot|unknown plus a normalized locator.
  classify)
    a="${2:-}"
    if [ -z "$a" ]; then echo "ARTIFACT_TYPE=unknown"; echo "REASON=no-argument"; exit 0; fi
    case "$a" in
      http://*|https://*)
        echo "ARTIFACT_TYPE=url"; echo "LOCATOR=$a"
        case "$a" in
          *claude.site*|*claude.ai*|*.claude.com*) echo "AUTH_LIKELY=yes  # Claude design — reuse your Chrome session via the Playwright extension" ;;
          *) echo "AUTH_LIKELY=unknown" ;;
        esac
        ;;
      *)
        if [ ! -e "$a" ]; then echo "ARTIFACT_TYPE=unknown"; echo "REASON=path-not-found: $a"; exit 0; fi
        ext="${a##*.}"; ext="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"
        case "$ext" in
          html|htm) echo "ARTIFACT_TYPE=html"; echo "LOCATOR=file://$(cd "$(dirname "$a")" && pwd)/$(basename "$a")" ;;
          png|jpg|jpeg|gif|webp|avif) echo "ARTIFACT_TYPE=screenshot"; echo "LOCATOR=$(cd "$(dirname "$a")" && pwd)/$(basename "$a")" ;;
          *) echo "ARTIFACT_TYPE=unknown"; echo "REASON=unrecognized-extension: .$ext" ;;
        esac
        ;;
    esac
    ;;

  # tailwind-config <fe-root> — locate the project's Tailwind config so recon-extract
  # can snap computed values to the PROJECT'S real tokens, not the default palette.
  tailwind-config)
    root="${2:-.}"
    cfg=$(find "$root" -maxdepth 3 \( -name 'tailwind.config.*' -o -name 'theme.css' \) \
          -not -path '*/node_modules/*' 2>/dev/null | head -1)
    if [ -z "$cfg" ]; then
      # Tailwind v4 puts theme tokens in CSS via @theme — grep the main stylesheet.
      cfg=$(grep -rlE '@theme|@import +"tailwindcss"' "$root" --include='*.css' \
            -l 2>/dev/null | grep -v node_modules | head -1)
    fi
    if [ -n "$cfg" ]; then
      echo "TAILWIND_CONFIG=$cfg"
      # Surface any custom color tokens for the skill to fold into recon-extract opts.
      echo "----- color hints (best-effort grep) -----"
      grep -oE '("?[a-zA-Z0-9-]+"?[[:space:]]*:[[:space:]]*"#[0-9a-fA-F]{3,8}")|(--color-[a-zA-Z0-9-]+:[[:space:]]*#[0-9a-fA-F]{3,8})' "$cfg" 2>/dev/null | head -60
      echo "----- end -----"
    else
      echo "TAILWIND_CONFIG=none  # extractor falls back to the default Tailwind palette"
    fi
    ;;

  # serve <html-file> — start a transient static server rooted at the file's dir.
  # Prints SERVE_URL + SERVE_PID; the skill navigates to it, then calls `stop <pid>`.
  serve)
    f="${2:-}"
    if [ ! -f "$f" ]; then echo "SERVE_ERROR=file-not-found: $f" >&2; exit 2; fi
    dir=$(cd "$(dirname "$f")" && pwd); base=$(basename "$f")
    port=0
    if command -v python3 >/dev/null 2>&1; then
      # Bind to an ephemeral port; python prints the chosen port on first line.
      ( cd "$dir" && python3 -c 'import http.server,socketserver,sys
with socketserver.TCPServer(("127.0.0.1",0), http.server.SimpleHTTPRequestHandler) as s:
    print(s.server_address[1], flush=True); s.serve_forever()' ) >/tmp/shipkit-recon-serve.$$ 2>&1 &
      pid=$!
      # wait for the port line
      for _ in $(seq 1 20); do
        port=$(head -1 /tmp/shipkit-recon-serve.$$ 2>/dev/null)
        [[ "$port" =~ ^[0-9]+$ ]] && break
        sleep 0.1
      done
      if [[ "$port" =~ ^[0-9]+$ ]]; then
        echo "SERVE_URL=http://127.0.0.1:$port/$base"
        echo "SERVE_PID=$pid"
      else
        kill "$pid" 2>/dev/null; echo "SERVE_ERROR=python-server-failed" >&2; exit 2
      fi
    else
      echo "SERVE_ERROR=python3-not-found — use the file:// LOCATOR from classify instead" >&2; exit 2
    fi
    ;;

  stop)
    pid="${2:-}"
    if [ -n "$pid" ]; then kill "$pid" 2>/dev/null && echo "STOPPED=$pid" || echo "STOP_NOOP=$pid"; fi
    rm -f /tmp/shipkit-recon-serve.* 2>/dev/null
    ;;

  *)
    echo "usage: recon.sh {classify <path|url>|tailwind-config <fe-root>|serve <html>|stop <pid>}" >&2
    exit 2
    ;;
esac
