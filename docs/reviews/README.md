# Independent Review Records

This directory preserves independent review verdicts for security-critical
changes. A review record describes the implementation that was inspected,
reproducible evidence, required remediation, accepted residual risks, and the
conditions for changing the verdict.

| Date | Scope | Verdict |
|---|---|---|
| [2026-07-26](2026-07-26-pr-25-independent-review.md) | PR #25, P0-04 native command guard | Not ready to merge |

A passing test suite does not override an open blocking finding. A verdict can
change only after the implementation, installed artifact, and relevant live
behavior have been revalidated and independently reviewed.
