#!/usr/bin/env python3
"""Manage the link-audit issue: update with trends, close when clean, track history."""
import json, os, re, subprocess, sys
from datetime import date

REPORT_FILE = "link-report.json"
LABEL = "links"
TODAY = date.today().isoformat()
RUN_URL = os.environ.get("RUN_URL", "")

# -- State embedded in issue body as an HTML comment ---------------------------
STATE_MARKER_RE = re.compile(r"<!-- link-health-state\n(.*?)\n-->", re.DOTALL)


def load_report() -> dict:
    with open(REPORT_FILE) as f:
        return json.load(f)


def load_previous_state(issue_body: str) -> dict | None:
    m = STATE_MARKER_RE.search(issue_body)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def build_state(current_broken: list[dict], previous: dict | None) -> dict:
    """Build new state and compute trend data."""
    prev_urls: dict[str, dict] = (previous or {}).get("urls", {})
    cur_set = {e["url"] for e in current_broken}
    prev_set = set(prev_urls.keys())

    new_urls = cur_set - prev_set
    fixed_urls = prev_set - cur_set
    persistent = cur_set & prev_set

    # Build new url map: preserve first_seen for persistent, record today for new
    urls: dict[str, dict] = {}
    for entry in current_broken:
        u = entry["url"]
        first_seen = prev_urls[u]["first_seen"] if u in prev_urls else TODAY
        urls[u] = {"status": entry["code"], "first_seen": first_seen}

    return {
        "last_run": TODAY,
        "urls": urls,
        "trend": {
            "new": sorted(new_urls),
            "fixed": sorted(fixed_urls),
            "persistent": len(persistent),
        },
    }


AUTOFIX_FILE = "auto-fix-report.json"


def load_autofix() -> dict | None:
    """Load Level 1 deterministic auto-fix suggestions if available."""
    if not os.path.exists(AUTOFIX_FILE):
        return None
    try:
        with open(AUTOFIX_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def build_body(report: dict, state: dict) -> str:
    broken = report.get("broken_urls", [])
    trend = state.get("trend", {})
    new_links = trend.get("new", [])
    fixed_links = trend.get("fixed", [])
    autofix = load_autofix()
    suggestions = (autofix or {}).get("suggestions", [])
    suggested_urls = {s["broken"]: s["suggested"] for s in suggestions}

    lines = [
        "## Broken external links",
        "",
        f"Checked **{report['checked']}** URLs across all markdown files. "
        f"**{len(broken)}** are unreachable.",
        "",
    ]

    if broken:
        lines += [
            "| Status | URL | Auto-fix | First seen |",
            "|--------|-----|----------|------------|",
        ]
        urls_map = state.get("urls", {})
        for entry in broken:
            u = entry["url"]
            fs = urls_map.get(u, {}).get("first_seen", TODAY)
            fix = suggested_urls.get(u, "")
            if fix:
                fix = f"[→ suggested](#auto-fix-suggestions)"
            lines.append(f"| {entry['code']} | {u} | {fix} | {fs} |")
        lines.append("")

    # Trend summary
    if new_links or fixed_links or trend.get("persistent"):
        lines.append("### Trend")
        lines.append("")
        if new_links:
            lines.append(f"- New this week: **{len(new_links)}**")
        if fixed_links:
            lines.append(f"- Fixed this week: **{len(fixed_links)}**")
        if trend.get("persistent"):
            lines.append(f"- Persistent: **{trend['persistent']}**")
        lines.append("")

    # Auto-fix suggestions (Level 1)
    if suggestions:
        lines += [
            '<a name="auto-fix-suggestions"></a>',
            "### Auto-fix suggestions (Level 1)",
            "",
            "These URLs have deterministic corrections — no LLM involved:",
            "",
            "| Broken | Suggested replacement |",
            "|--------|----------------------|",
        ]
        for s in suggestions:
            lines.append(f"| {s['broken']} | {s['suggested']} |")
        lines += [
            "",
            "> Apply these by running: `sed -i 's|OLD_URL|NEW_URL|g' $(grep -rl OLD_URL .)`",
            "> Then run `bash tests/validate-links.sh` to verify.",
            "",
        ]

    lines += [
        "### How to fix",
        "",
        "1. Review auto-fix suggestions above (if any) and apply with `sed`",
        "2. For unsuggested URLs, verify if permanently moved or temporarily down",
        "3. Update the URL in the source markdown file",
        "4. Run `bash tests/validate-links.sh` locally to verify",
    ]
    if RUN_URL:
        lines.append(f"5. [View full CI run]({RUN_URL}) for detailed logs")
    lines.append("")

    # Embed state as HTML comment for next run
    state_json = json.dumps(state, indent=2)
    lines.append(f"<!-- link-health-state\n{state_json}\n-->")

    return "\n".join(lines)


def get_existing_issue() -> dict | None:
    r = subprocess.run(
        ["gh", "issue", "list", "--label", LABEL, "--state", "all",
         "--limit", "1", "--json", "number,state,body"],
        capture_output=True, text=True,
    )
    if not r.stdout.strip():
        return None
    issues = json.loads(r.stdout)
    return issues[0] if issues else None


def close_issue(number: int) -> None:
    subprocess.run(
        ["gh", "issue", "close", str(number),
         "--reason", "completed",
         "--comment", "All external links are now reachable."],
        check=True,
    )
    print(f"Closed issue #{number} — all links reachable")


def reopen_issue(number: int) -> None:
    subprocess.run(["gh", "issue", "reopen", str(number)], check=True)
    print(f"Reopened issue #{number}")


def update_issue(number: int, body: str) -> None:
    subprocess.run(
        ["gh", "issue", "edit", str(number), "--body", body],
        check=True,
    )
    print(f"Updated issue #{number}")


def create_issue(title: str, body: str) -> None:
    subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body,
         "--label", "maintenance", "--label", LABEL],
        check=True,
    )
    print(f"Created new issue: {title}")


def main() -> None:
    report = load_report()
    broken = report.get("broken_urls", [])

    existing = get_existing_issue()
    previous = None
    if existing:
        previous = load_previous_state(existing.get("body", ""))

    state = build_state(broken, previous)
    body = build_body(report, state)

    if not broken:
        if existing and existing["state"] == "OPEN":
            close_issue(existing["number"])
        else:
            print("No broken links and no open issue — nothing to do")
        return

    # Broken links exist — create or update issue
    title = f"Link audit — {TODAY}"

    if existing:
        num = existing["number"]
        if existing["state"] == "CLOSED":
            reopen_issue(num)
        update_issue(num, body)
    else:
        create_issue(title, body)


if __name__ == "__main__":
    main()
