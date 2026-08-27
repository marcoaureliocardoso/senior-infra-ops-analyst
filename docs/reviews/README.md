# Independent Review Records

This directory preserves independent review verdicts for security-critical
changes. A review record describes the implementation that was inspected,
reproducible evidence, required remediation, accepted residual risks, and the
conditions for changing the verdict.

| Date | Scope | Verdict |
|---|---|---|
| [2026-08-27](2026-08-26-p0-06-guarantee-separation-review.md) | P0-06 deterministic guarantee separation | Approved; no Critical or Important finding remains |
| [2026-07-26, updated 2026-07-28](2026-07-26-pr-25-independent-review.md) | PR #25, P0-04 native command guard | Changes required; remediation pending independent re-review; RV-11 accepted exception |

A passing test suite does not override an open blocking finding. A verdict can
change only after the implementation, installed artifact, and relevant live
behavior have been revalidated and independently reviewed.
