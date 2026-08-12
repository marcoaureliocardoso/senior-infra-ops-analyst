# P0-04A Pending Acceptance and Merge Gates Design

**Date:** 2026-08-12
**Status:** Approved for documentation

## Objective

Make the remaining P0-04A acceptance and merge work explicit without implying
that implementation readiness satisfies the required real automatic-compaction
acceptance scenario. Exclude credential cleanup and unrelated operational work.

## Canonical pending-gate matrix

| Gate | Current evidence | Completion condition |
|---|---|---|
| Real automatic acceptance | The repaired strict diagnostic confirmed a native 1,000,000-token window and reached 10% under an isolated 5% threshold, but no completed ordered automatic pair occurred within 600 seconds. | Observe one real ordered `PreCompact(auto)` then `PostCompact(auto)` pair on the reviewed head. |
| Structural classification | Cleanup proves `complete_pair=false` but removes the content-free event file, so the terminal record cannot distinguish `pre_only` from `no_pre`. | Retain only a sanitized closed classification of `complete_pair`, `pre_only`, or `no_pre`; never retain transcript, prompt, summary, raw hook input, or secret. |
| Alternative acceptance decision | Repeated real attempts remain inconclusive despite native capacity confirmation and pressure above the isolated threshold. | If direct observation remains infeasible, obtain explicit operator approval for a revised acceptance criterion before treating the live gate as satisfied. |
| Final reviewed head | Implementation review and CI/Security are green on the current evidence head, but any further change creates a new head. | Obtain independent review with no release-blocking findings and green CI/Security on the exact final head. |
| Merge and TODO completion | PR #32 remains draft and P0-04A remains pending. | Merge the approved final head into `main`; only then mark P0-04A complete in the definitive non-versioned TODO. |

## Documentation placement

- The definitive non-versioned TODO receives the full matrix as the current
  P0-04A pending state while its status and checkboxes remain open.
- ADR-005 receives the architectural pending gates and the distinction between
  a required acceptance result and an optional diagnostic improvement.
- Validation notes receive the evidence-specific matrix, including exact
  observed values and the proof limitation.
- PR #32 receives a concise checklist linked to the same completion conditions
  and remains draft.

## Consistency rules

- Do not describe implementation, deterministic validation, review, CI, or
  Security as the missing P0-04A behavior.
- Do not infer `no_pre` from the fourth run; record only
  `complete_pair=false` and the unresolved `pre_only` versus `no_pre` split.
- Treat sanitized structural classification as a diagnostic improvement, not a
  substitute for the ordered real pair.
- Do not weaken the live acceptance criterion without a new explicit operator
  decision.
- Do not mark the TODO complete or merge the PR as part of this documentation
  update.

## Validation

- Run `git diff --check`, architecture-document tests, content validation, and
  markdown lint over every changed versioned document.
- Request independent read-only review of the exact final diff.
- Commit and push the documentation to the existing PR branch.
- Require CI and Security success on the resulting head.
