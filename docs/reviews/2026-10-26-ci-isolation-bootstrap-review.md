# CI isolation bootstrap review and author remediation

## Official APT action suffix model - 2026-10-27
The previous exact-head hosted diagnostic identified INST_SUFFIX at line28,
length126, with cleanup PASSED. The operator requested strict modeling of the
official forms, not blanket suffix removal. Upstream Describe/RealInstall/
RealConfigure/RealRemove/ShortBreaks/Go emit relational blocks only for Inst,
followed optionally by a ShortBreaks list; configuration/removal records permit only that list.

The new positional recognizer validates the entire suffix, exact whitespace,
bounded full names, ordering and multiplicity. It returns the same core action
groups; annotations are never returned as actions or authority. Native command
success and all coherence, package-policy and postcondition checks remain.
Five new test methods pin official forms, targeted-dependency and unsafe-policy
behavior, malformed/foreign/reordered suffixes and incomplete proposals. The
diagnostic examples now use invalid suffixes so known official syntax no longer
has an obsolete rejection expectation. Review and immutable/hosted evidence are
pending at this record's creation. No actual received line was captured.

## Approved structural APT diagnostic increment - 2026-10-27
After the fresh four-finding repair, hosted CI40534516818 at be6f470 rejected
an APT simulation line with APT_SIMULATION_UNRECOGNIZED and passed cleanup.
No received line or artifact survived; the root trigger could not be recovered.
Official APT simulation sources and six pure synthetic probes demonstrated that
multiple structural forms share this error, not which one occurred in CI.

The operator approved one diagnostic increment and one exact-head CI validation.
Schema3 adds nullable aptRejection={kind,line,length}, with a finite kind and
bounded numeric fields only. Existing rejection, operational commands, capture,
privileges and Nori versions remain unchanged. No raw line, content hash or
package identity may enter the projection; cleanup cannot replace the primary
detail. Focused CI suites passed after RED-to-GREEN controls. A fresh independent
read-only review of be6f470..75767fd and all nine changed files found no actionable
Critical/Important/Minor findings. It verified the unchanged acceptance path,
strict finite projection and cleanup preservation without rerunning tests.
The actual prior APT trigger, whole-package/hosted behavior, whole-PR security,
operational root/provider/native acceptance and merge/release were not certified.
The author subsequently ran the complete immutable gate at
`75767fd92071ad0a0697b73c097e7efe06766aa2`: exit0 in1476.21 seconds, no timeout,
all613 canonical files/archive digest unchanged, disposable cleanup proved and
identical Windows-preserved receipt. Exact hashes are in validation notes.
The one authorized exact-head hosted diagnostic validation remains pending.

## Fresh review and four-finding author fix pass - 2026-10-27
Three fresh independent ordinary domain reviews inspected the published
`cd78c2a472a219636fc1cadf59387b7017f74e77` candidate against the unchanged base.
They reported two P2 and two P3 findings, all approved for correction by the
operator. This is their single author TDD repair pass, not a fresh independent
approval or a formal security scan.

| Finding | Reproduction and correction |
|---|---|
| P2 finite APT parser errors lost as UNKNOWN_ERROR | Four real parser failures passed through prepare, cleanup and stdout projection reproduced the loss. Add only the four existing APT_SIMULATION parser codes to the closed diagnostic enum; arbitrary messages remain UNKNOWN_ERROR. |
| P2 Playwright names matched different controls | Real adapter methods with documented-surface doubles accepted longer or case-different names. Require exact matching for named locators; positive controls cover fill/select/click/submit/inspect/verify and negatives prove no wrong dispatch. |
| P3 legacy stream tool ownership | Synthetic traces accepted user-owned calls, assistant-owned results and conflicting supplied message roles. Enforce native event ownership and consistent supplied roles while preserving omitted historical inner roles. |
| P3 duplicate JSON fields hid errors | Duplicate terminal, init and nested fields overwrote failures or session metadata. Reuse the strict object-pairs parser and reject the whole ambiguous sample, including later success records. |

All four regressions failed before the implementation changes. The first
Playwright GREEN run exposed an overly specific assertion on a private double
error; the assertion now uses the adapter's existing sanitized public failure
and separately verifies zero protected dispatch. No production error handling
was relaxed. Browser component advances to1.0.4; command stays1.2.1.

Author verification: whole browser227 pass plus one real-browser opt-in skip;
legacy144, SDK/resume29 and all six affected CI groups passed. Package metadata
and quality checks passed. The immutable full-package gate at
`a041214992d34d659c12dfc850a1377a47aa9a36` passed in1473.52 seconds, exit0,
no timeout; all613 canonical files and the archive digest remained unchanged,
with disposable cleanup proved and an identical Windows-preserved receipt.
Exact hashes and exclusions are in the validation notes. This author repair
pass is not a second independent review, native acceptance or hosted approval.

The exact published cd78c2a CI40415866653 failed at
PACKAGE_UPGRADE_SIMULATE with UNKNOWN_ERROR and cleanup PASSED. The six other
CI jobs and Security40415866666 passed. These reviews establish diagnostic loss,
not the actual hosted APT exception or a parser grammar defect. Hosted and local
qualification remain separate. No real browser/provider/native session, raw
diagnostic retention, manual hosted retry, merge or release is authorized by
these repairs. Formal security-diff-scan remains unavailable: the earlier setup
failed before scanId; ordinary reviews and hosted Security do not replace it.

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
The complete provider-free gate passed at `e614e3c` in1481.213 seconds with613
canonical files unchanged and disposable cleanup proved; its synchronized receipt
was preserved byte-for-byte on Windows. The prior `d11513a` gate failed at two
stale release-history version assertions and was retained, not rewritten. Those
test-only pins were corrected without relaxing drift rejection. Exact hashes,
exclusions and subsequent evidence-only documentation are in the validation notes.
This local pass does not establish exact-head hosted isolation or native acceptance.

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
