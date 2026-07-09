---
title: "🔗 Broken external links detected — {{ date | date('YYYY-MM-DD') }}"
labels: [maintenance, links]
---

Scheduled link validation failed. The following URLs may be unreachable.

Run `bash tests/validate-links.sh` locally to reproduce and update `references/external-sources.md` with working URLs.

<details>
<summary>Validation output</summary>

```text
{{ env.GITHUB_WORKFLOW }} run #{{ env.GITHUB_RUN_NUMBER }}
See run logs for full output: {{ env.GITHUB_SERVER_URL }}/{{ env.GITHUB_REPOSITORY }}/actions/runs/{{ env.GITHUB_RUN_ID }}
```

</details>
