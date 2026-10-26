# CI isolation bootstrap review and author remediation

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
No second independent review occurred: remediation is author-verified under the
approved single-review/single-fix-pass method, not a new independent approval.

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
A new immutable full gate is required for the corrected candidate.

Hostile root administrators/malicious workflows are outside the trusted-runner
model. Claude/provider/browser/twelve-role acceptance, earlier PR changes,
formal full-PR security certification and legal sufficiency of notices were not
certified. No native authorization, merge or release follows from this record.
