#!/usr/bin/env bash
# Optional link checker. It requires curl and internet access.
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found; skipping link validation"
  exit 0
fi
status=0
urls=$(grep -Eo 'https?://[^) ]+' references/external-sources.md | sort -u)
if [ -z "$urls" ]; then echo "No URLs found"; exit 1; fi
while IFS= read -r url; do
  code=$(curl -L -I --max-time 15 -o /dev/null -s -w '%{http_code}' "$url" || true)
  case "$code" in
    2*|3*|401|403) echo "OK $code $url" ;;
    429)
      sleep 3
      code=$(curl -L -I --max-time 15 -o /dev/null -s -w '%{http_code}' "$url" || true)
      case "$code" in
        2*|3*|401|403) echo "OK $code $url (after 429 retry)" ;;
        *) echo "WARN $code $url (after 429 retry)"; status=1 ;;
      esac
      ;;
    *) echo "WARN $code $url"; status=1 ;;
  esac
  sleep 0.5
done <<< "$urls"
exit "$status"
