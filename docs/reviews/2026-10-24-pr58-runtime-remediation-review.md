# PR 58 runtime remediation review

## Range and verdict

One fresh independent reviewer examined the complete approved remediation range
91cd9416adf5ce0d92deda312be817dc97169048 through
70381a53d6ddc8aa8a1f30de595584a53d314720, the plan, specification, ledger and
interacting unchanged callers. No Critical or Important issue was found.
This is an incremental correctness review, not full-PR security certification.
The overall PR is not ready to merge because separate gates remain blocked.

The reviewer confirmed that configuration validation fails before authority
staging or dispatch, explicit authentication remains usable, negative desired
state after possible writes remains unknown, and lifecycle faults latch rejection.
Independent memory-only controls accepted a valid stream/successful passive hook
and rejected a late reset or failed hook. No real Claude, provider, browser,
operator configuration or credential was accessed by the review.

## Deferred Minor

In tests/browser_operations_live.py, the new system-subtype membership check can
raise TypeError for an unhashable subtype such as a list instead of returning a
bounded rejected sample. The independent reviewer reproduced this. It fails
closed, not as false acceptance. The parser exception skips immediate local file
deletion, but the shell EXIT trap removes and verifies the validated disposable
work directory, including streams, prompts, transcripts and native history.
No retention bypass was identified. This remains deferred under the approved
single-review method; no second review or additional fix pass is claimed.

## Execution and review rulings

- Validation preparation accepts credential-class fill/select and interactive
  clicks only on explicit auth origins; service navigation/inspection remain.
  Cost if wrong: service-only interactive manifests fail closed and need redesign.
- A negative desired-state predicate retains UNKNOWN; only independently proven
  pre-dispatch paths retain NOT_APPLIED. Cost if wrong: conservative reconciliation
  is required even for a genuinely unapplied operation.
- Runner error tests use the existing BROWSER_RUNNER prefix. Cost if wrong:
  diagnostic spelling only; behavioral rejection assertions remain unchanged.
- Prepare disjoint Task 2 tests during Task 1 repeated validation. Cost if wrong:
  combined task bases, with file-scoped commits preserving separate changes.
- Passive hooks retain existing absent/success outcome and absent/integer-zero
  exit forms with bounded identity and exact session. They do not prove native
  guard coverage. Cost if wrong: conservative rejection of malformed/foreign hooks.
- Push the independently reviewed/focused-tested candidate while its immutable
  gate runs, without readiness or merge claims. Cost if wrong: another corrective
  commit and CI run may be required.
- Inherited malformed event/tool discriminators remain outside the focused repair.
  Cost if wrong: broader rejected-input diagnostics need separate hardening.
- Other legacy system events and complete passive-hook pairing remain unqualified.
  Cost if wrong: those wider evidence protocols require dedicated qualification.
- Trusted-envelope classifications retain their existing trust boundary; this
  correction cannot prove that an operator correctly classifies every field or
  origin. Cost if wrong: mistaken designations require separate policy redesign.
- Actual browser/provider/native approval and SDK shutdown qualification remain
  pending. Cost if wrong: native compatibility stays unproved; no grant is renewed.
- Hosted Bubblewrap policy stays separately blocked; no host-policy adaptation is
  approved here. Cost if wrong: that runner cannot make this PR mergeable yet.
- Historical PR changes outside the correction range are not re-reviewed.
  Cost if wrong: inherited defects remain subject to separate review and gates.
- Complete package evidence is author-observed and exact-source-bound, not
  independently rerun by the reviewer. Cost if wrong: no package pass may be
  claimed without the corresponding immutable result and cleanup proof.

## Verification boundary

Focused and final package evidence, explicit skips and exact-head hosted status
are recorded in [validation notes](../../tests/validation-notes.md).
The reviewer did not independently observe the concurrent full-package run.
No merge, release, native acceptance or definitive TODO completion follows.
