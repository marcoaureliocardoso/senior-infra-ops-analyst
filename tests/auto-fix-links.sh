#!/usr/bin/env bash
# Level 1 deterministic link auto-fix.
# Tries known URL transformations for common link rot patterns.
# Input:  link-report.json from validate-links.sh --json
# Output: JSON with candidate URLs for each broken link (only reachable ones)
set -euo pipefail
cd "$(dirname "$0")/.."

REPORT="${1:-link-report.json}"
if [ ! -f "$REPORT" ]; then
  echo '{"status":"error","reason":"report file not found"}'
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo '{"status":"skipped","reason":"curl not found"}'
  exit 0
fi

# --- Pattern handlers -------------------------------------------------
# Each returns a space-separated list of candidate URLs to try.

try_rfc_editor() {
  local url="$1"
  # rfc-editor.org/rfc/rfcNNNN → try .html and datatracker
  local rfc
  rfc=$(echo "$url" | grep -oP 'rfc\d+')
  [ -z "$rfc" ] && return
  echo "https://www.rfc-editor.org/rfc/$rfc.html"
  echo "https://datatracker.ietf.org/doc/html/$rfc"
}

try_man7() {
  local url="$1"
  # man7.org/.../journalctl.1.html → try without .html
  if [[ "$url" == *man7.org* ]]; then
    echo "${url%.html}"
    echo "${url%.html}.html"  # original, retried
  fi
}

try_freedesktop() {
  local url="$1"
  # freedesktop.org/.../journalctl.html → try without .html, try /latest/ → /stable/
  if [[ "$url" == *freedesktop.org* ]]; then
    echo "${url%.html}"
    echo "${url//\/latest\//\/stable\/}"
  fi
}

try_microsoft_learn() {
  local url="$1"
  # learn.microsoft.com — HEAD often returns 404 but GET works.
  # Try removing trailing segments one by one.
  if [[ "$url" == *learn.microsoft.com* ]]; then
    # Try the URL as-is with GET instead of HEAD (validate-links.sh uses HEAD)
    echo "$url"
    # Try parent path
    echo "${url%/*}"
  fi
}

# --- Main logic -------------------------------------------------------
check_url() {
  local url="$1"
  local code
  code=$(curl -L -I --max-time 10 -o /dev/null -s -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  case "$code" in
    2*|3*|401|403) return 0 ;;
    *) return 1 ;;
  esac
}

broken_urls=$(python3 -c "
import json
with open('$REPORT') as f:
    report = json.load(f)
for entry in report.get('broken_urls', []):
    print(entry['url'])
")

if [ -z "$broken_urls" ]; then
  echo '{"status":"ok","suggestions":[]}'
  exit 0
fi

suggestions=""
while IFS= read -r url; do
  [ -z "$url" ] && continue
  candidates=""

  # Try pattern-specific handlers
  if [[ "$url" == *rfc-editor.org* ]]; then
    candidates=$(try_rfc_editor "$url")
  elif [[ "$url" == *man7.org* ]]; then
    candidates=$(try_man7 "$url")
  elif [[ "$url" == *freedesktop.org* ]]; then
    candidates=$(try_freedesktop "$url")
  elif [[ "$url" == *learn.microsoft.com* ]]; then
    candidates=$(try_microsoft_learn "$url")
  fi

  # Test each candidate
  for candidate in $candidates; do
    [ "$candidate" = "$url" ] && continue  # skip original
    sleep 0.3
    if check_url "$candidate"; then
      suggestions+="{\"broken\":\"$url\",\"suggested\":\"$candidate\",\"pattern\":\"deterministic\"},"
      break  # first working candidate wins
    fi
  done
done <<< "$broken_urls"

suggestions="${suggestions%,}"
echo "{\"status\":\"ok\",\"suggestions\":[$suggestions]}"
