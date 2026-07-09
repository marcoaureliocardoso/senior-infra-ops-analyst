#!/usr/bin/env bash
# Validate external links in all markdown files.
# Usage:
#   bash tests/validate-links.sh          # human-readable output, exits non-zero on broken links
#   bash tests/validate-links.sh --json   # JSON report to stdout
set -euo pipefail
cd "$(dirname "$0")/.."

json_output=false
if [[ "${1:-}" == "--json" ]]; then
  json_output=true
fi

if ! command -v curl >/dev/null 2>&1; then
  if $json_output; then
    echo '{"status":"skipped","reason":"curl not found","broken":[]}'
  else
    echo "curl not found; skipping link validation"
  fi
  exit 0
fi

# Extract all https?:// URLs from all markdown files.
# Filters out placeholder URLs (<host>, <prometheus>, etc.) and strips trailing backticks.
urls=$(find . -name '*.md' \
  -not -path './.git/*' \
  -not -path './.worktrees/*' \
  -exec grep -Eo 'https?://[^])>[:space:]]+' {} \; \
  | sed -e 's/[.,;:]*$//' -e 's/`$//' \
  | grep -v '[<>]' \
  | sort -u)

if [ -z "$urls" ]; then
  if $json_output; then
    echo '{"status":"ok","checked":0,"broken":[]}'
  else
    echo "No external URLs found in markdown files"
  fi
  exit 0
fi

ok_count=0
broken=()
total=0

check_url() {
  local url="$1"
  local code
  code=$(curl -L -I --max-time 15 -o /dev/null -s -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  case "$code" in
    2*|3*|401|403)
      ok_count=$((ok_count + 1))
      ;;
    429)
      sleep 3
      code=$(curl -L -I --max-time 15 -o /dev/null -s -w '%{http_code}' "$url" 2>/dev/null || echo "000")
      case "$code" in
        2*|3*|401|403) ok_count=$((ok_count + 1)) ;;
        *) broken+=("$code $url") ;;
      esac
      ;;
    *)
      broken+=("$code $url")
      ;;
  esac
}

while IFS= read -r url; do
  [ -z "$url" ] && continue
  check_url "$url"
  total=$((total + 1))
  sleep 0.5
done <<< "$urls"

# --- JSON report ---
if $json_output; then
  entries=""
  for entry in "${broken[@]}"; do
    code="${entry%% *}"
    url="${entry#* }"
    entries+="{\"code\":\"$code\",\"url\":\"$url\"},"
  done
  entries="${entries%,}"
  echo "{\"status\":\"$([ ${#broken[@]} -eq 0 ] && echo 'ok' || echo 'broken')\",\"checked\":$total,\"ok\":$ok_count,\"broken\":${#broken[@]},\"broken_urls\":[$entries]}"
  [ ${#broken[@]} -eq 0 ]
  exit
fi

# --- Human-readable output ---
echo "Checked $total URLs: $ok_count reachable, ${#broken[@]} broken"

if [ ${#broken[@]} -gt 0 ]; then
  echo ""
  echo "=== BROKEN LINKS ==="
  for entry in "${broken[@]}"; do
    echo "  $entry"
  done
  echo ""
  echo "${#broken[@]} broken link(s) found."
  exit 1
fi

echo "All external links reachable."
