# CI isolation bootstrap review and author remediation

## Operator-requested resumed PR review
The three original ordinary engineering reviewers resumed at
`8846bee1aa47834cec95c206e8e1cd90514868d4..8e7429be1c23dea1cdb368432dee976e845b111b`
after the service-limit interruption. The operator included all eight confirmed
P2 findings in one author TDD fix wave, alongside bounded CI failure diagnostics.

| Finding | Observable author correction |
|---|---|
| Native role declared through untrusted CLI | Final guard and approval staging require the native actor's role; main cannot claim an executor and an audit actor cannot stage or dispatch its workflow. |
| Legacy close/validate denied despite valid operation | Resolve the absent origin only from the exact live session/native-role operation; missing, foreign, expired or mode-incompatible bindings reject, and ALWAYS_ASK remains. |
| Puppeteer role parsed as accessible name | Use explicit role/name ARIA attributes with lossless literal delimiters; names requiring unsupported quoting reject rather than being rewritten. |
| Puppeteer Locator/ElementHandle API mismatch | Documented fill and waitHandle/ElementHandle APIs replace Playwright-only calls; handles are disposed on success, failure and late acquisition, with lifetime/origin checks. |
| Discovery without ToolSearch rejected | Zero calls are valid only for discovery when native init did not advertise ToolSearch; other stages retain exactly one completed expected call. |
| Legacy lifecycle faults masked by success | Require init before calls, retain reset/compaction/unknown-system/error/deferred/denied faults through EOF, including after result success. |
| SDK resume lifecycle faults masked by success | Reject the same failure/completeness metadata before SDK_VALIDATED; only understood successful hooks are benign. |
| Frozen general candidate unsafe disposition aborted | After proving no proposal/package/hold drift, record SKIP_UNSAFE and continue separately assessed explicit dependencies; unsafe dependencies and unknown state still block. |

All reproductions use synthetic/native-shaped fixtures or documented API-surface
doubles, not actual Claude/provider/browser execution or privileged host package
changes. The Puppeteer guide, Locator API and upstream ARIA parser were consulted;
no library version was pinned or dependency installed. Primary contracts:
[page interactions](https://pptr.dev/guides/page-interactions),
[Locator API](https://pptr.dev/api/puppeteer.locator) and
[ARIA query parser](https://github.com/puppeteer/puppeteer/blob/main/packages/puppeteer-core/src/common/AriaQueryHandler.ts).
Finite CI diagnostics
preserve the first failure before cleanup and exclude raw content/host identities.

Coverage: the browser review inspected production browser modules, launcher,
workflow/effects, credentials/origins/lifetimes/artifacts/settings, changed guard
paths and relevant tests/docs. CI review covered the three workflows, CI modules,
lock/template/fixtures and changed tests/wiring. Harness review covered core
startup/measurement/permission/context/state/provisioning/offline orchestration
and selected reducers/history paths, not every line of the large PR/test corpus.
Unchanged workflow machinery outside integration was not exhaustively reviewed.

The formal security plugin rejected the linked worktree before issuing a scanId,
although native Git resolved its non-bare HEAD. No replacement scan or canonical
security report was fabricated. Ordinary reviews and hosted Security checks are
not formal full-PR certification or licensing/legal approval. Native/provider/
browser/twelve-role acceptance and platform kernel/process behavior remain
unqualified by these reviews; ADR-010's CAPABILITY_UNAVAILABLE gate is unchanged.
Author remediation is not an independent re-review or merge approval.

## Independent assessment
One read-only independent review inspected the immutable implementation range
`854e77c6681c30875fc66ea34005b23eb92d5e11..cbac3c7dfad441e0291ec8791ff9fc4052fb54fd`,
its approved design/plan, privileged worker, actual Linux transport, tests and
three full-validation workflows. Verdict: **changes required**, six Important
findings, no Critical finding. It did not run privileged or authenticated probes.
The reviewed diff SHA-256 was
`db4d4752f2943726859e802ee82d44416f9fd5d4514b920095ca51770650e081`.

## Author's single TDD remediation pass
| Finding | Reproduction and correction |
|---|---|
| Hosted `/opt` is world-writable | Hosted-layout control rejected the original ancestors; protected `/var/lib` and `/var/cache` chains pass without host permission repair. |
| sudo resets package safety environment | A real synthetic reset subprocess lost the settings; fixed values are now supplied after elevation. No real sudo test ran locally. |
| Native APT narrative rejected | Exact manual-mark and mixed phasing fixtures failed, then passed; unknown or incoherent records still reject. |
| New Multi-Arch identity mismatch | First-install postcondition failed on a qualified dpkg key; validated archive metadata now determines the expected key. |
| AppArmor substring false attestation | Child-only, foreign-suffix and extra-component labels falsely passed; exact two-component enforcement now rejects them. |
| Partial policy publication/false clean | Top-level cleanup reported success without checking the unmarked target; atomic ownership intent now precedes exclusive publication and cleanup always checks an installed runtime's expected policy. |

Real temporary-filesystem controls cover interrupted publication, substituted
inodes and unload failure. They do not establish hosted kernel/parser behavior.
That bootstrap remediation had no second independent review; it was
author-verified under the approved single-review/single-fix-pass method, not a
new independent approval. The later operator-requested resumed PR review is
recorded separately above.

## Deferred minors
- Diagnosis and optional policy arming do not share one 120-second sub-budget;
  the outer 600-second prepare bound remains.
- The structural report omits held/deferred counts, package identities and runner
  image identity; its action count/status must not be interpreted as those fields.

## Boundaries not certified by this review
Hosted APT/build/parser/audit/cancellation behavior still requires exact-head CI.
The old concurrent immutable gate failed at the browser test's invalid-override
fallback, with source unchanged and disposable cleanup proved. A synthetic
recognized dependency reproduced that failure; a test-helper-only correction
now rejects invalid explicit overrides without changing production discovery.
The corrected immutable gate at `db4766f74cf62242d640ecb5b78edb81bd7600c5`
subsequently passed in 1480.972 seconds, exit0, source/archive identity unchanged
and disposable cleanup proved. Browser acceptance without opt-in and PowerShell
syntax checks without that runtime remained explicit exclusions. This local pass
does not replace exact-head hosted qualification or change the independent verdict.

An operator-authorized follow-up corrected the three workflows' runner report
bindings after GitHub rejected their job-level expressions before any job ran.
Step-scoped bindings and actual-script environment flow now have RED-to-GREEN
coverage. A full local pass at b260356 was recovered with intact source/archive
and cleanup proof after the first receipt was found unreadable; the original
attempt was preserved, not rewritten. See the dated validation notes for hashes,
timing and exclusions. This follow-up is author-verified, not a new independent
review or hosted-runtime approval.

Hostile root administrators/malicious workflows are outside the trusted-runner
model. Claude/provider/browser/twelve-role acceptance, earlier PR changes,
formal full-PR security certification and legal sufficiency of notices were not
certified. No native authorization, merge or release follows from this record.
