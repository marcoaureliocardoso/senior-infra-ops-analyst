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
# Double quotes and backticks delimit embedded JSON and Markdown examples.
# Preserve internal apostrophes (valid URL characters); trim wrapper quotes below.
urls=$(find . -name '*.md' \
  -not -path './.git/*' \
  -not -path './.worktrees/*' \
  -not -path './tests/reports/*' \
  -not -path './.superpowers/*' \
  -exec grep -Eo "https?://[^])>[:space:]\"\`]+" {} \; \
  | sed -e 's/[.,;:]*$//' -e 's/`$//' -e "s/'$//" -e 's/"$//' \
  | awk '!/[<>]/' \
  | LC_ALL=C sort -u \
  | while IFS= read -r url; do
      host=$(echo "$url" | sed -n 's|^https\?://\([^/:]*\).*|\1|p')
      # Skip bare hostnames (no dot — e.g., app02, localhost)
      [[ "$host" != *.* ]] && continue
      # Loopback fixture addresses are not external documentation links.
      [[ "$host" =~ ^127(\.[0-9]{1,3}){3}$ ]] && continue
      # Skip .local domains (RFC 6762 reserved — never publicly routable)
      [[ "$host" == *.local ]] && continue
      # Skip .invalid domains (RFC 2606 reserved for deliberately invalid names)
      [[ "$host" == *.invalid ]] && continue
      # Skip example/placeholder domains used in operational scenarios
      [[ "$host" == *.example.edu ]] && continue
      echo "$url"
    done)

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
  code=$(curl -q -L -I --max-time 15 -o /dev/null -s -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  case "$code" in
    2*|3*|401|403)
      ok_count=$((ok_count + 1))
      return
      ;;
    429)
      sleep 3
      code=$(curl -q -L -I --max-time 15 -o /dev/null -s -w '%{http_code}' "$url" 2>/dev/null || echo "000")
      case "$code" in
        2*|3*|401|403) ok_count=$((ok_count + 1)); return ;;
      esac
      ;;
  esac

  # HEAD failed — some servers reject HEAD but serve GET.
  # Try GET with Range: bytes=0-0 to verify reachability without downloading content.
  local get_code
  get_code=$(curl -q -L --range 0-0 --max-time 15 -o /dev/null -s -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  case "$get_code" in
    2*|3*|401|403)
      ok_count=$((ok_count + 1))
      return
      ;;
  esac

  # Both HEAD and GET failed — link is genuinely broken.
  broken+=("$code $url")
}

while IFS= read -r url; do
  [ -z "$url" ] && continue
  check_url "$url"
  total=$((total + 1))
  sleep 0.5
done <<< "$urls"

# --- JSON report ---
if $json_output; then
  # Use the project's existing Python runtime for JSON escaping, not shell
  # interpolation: a URL backslash must never become a JSON control escape.
  python3 - "$total" "$ok_count" "${broken[@]}" <<'PY'
import json
import sys

entries = [dict(zip(("code", "url"), entry.split(" ", 1))) for entry in sys.argv[3:]]
print(json.dumps({
    "status": "broken" if entries else "ok",
    "checked": int(sys.argv[1]), "ok": int(sys.argv[2]),
    "broken": len(entries), "broken_urls": entries,
}))
PY
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
