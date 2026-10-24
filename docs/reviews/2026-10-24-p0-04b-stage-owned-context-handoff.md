# P0-04B stage-owned context: local handoff

## Outcome

The approved inline implementation is committed locally with one independent
review and one author TDD correction pass. Tested code:
8d1b596821ca67ba56fc882e212b94366b202906. This handoff is a later documentation-only
closeout, not a new native qualification or an independent re-review.

- Local focused verification:284 unittest methods passed, no skips, including
  the actual public SDK parser/options and memory-only lifecycle regression.
- Immutable full package gate: exit0,1,461.331s, no timeout;579 canonical files
  unchanged and owned export cleanup proved. The source archive SHA256 is
  d06890da118593412ab322c03d0774b5dc3620051437b841c252dd3ea69ed464.
- Package-platform/optional exclusions and the earlier unexplained failed gate
  are preserved in [validation notes](../../tests/validation-notes.md).
- Native: NOT_RUN; readiness CAPABILITY_UNAVAILABLE. Current public disconnect
  cancels its reader before transport close, so application-consumer lifetime
  cannot prove observation of late shutdown faults. The guard blocks actual SDK
  connection and native reservation. No version pin, private-state workaround,
  extra observer/query, automatic retry or production transport replacement.
- Provider/live: EXCLUDED. Twelve-role/browser acceptance: BLOCKED/unproved.
  Remote CI/Security: NOT_RUN. Operational guards remain CONFIGURED_UNPROVEN.
- No push, PR, merge, release or definitive TODO completion. Version0.15.0 remains
  unchanged. The existing branch/worktree is preserved pending operator choice.

The [review record](2026-10-24-p0-04b-stage-owned-context-review.md) retains both
Important findings and their causal boundary. Their author fixes passed TDD;
no second review occurred. The earlier one-client provenance artifact remains
immutable and is not promoted into four-stage or full P0-04B acceptance.

## Exhaustive rulings and costs, in execution order

1. Use host Git plus apply_patch bookkeeping instead of Git-dependent WSL skill
   helpers, because the linked worktree uses a Windows-style gitdir pointer.
   Cost: manual ledger verification; no metadata/global Git configuration edits.
2. Normalize approved-plan headings to `Task N` for the helper parser.
   Cost: mechanical text changes only; no semantic requirements changed.
3. Test operator-home exclusion on mount sources, not all namespace arguments:
   sanitized HOME=/tmp also names an empty namespace directory. Cost: tests must
   distinguish empty paths from host mounts; a real zero-CLI namespace audit
   independently checks isolation.
4. Overlap the final read-only review with the original immutable package gate
   on identical committed bytes. Cost: corrections require new affected tests and
   a new immutable full gate; the earlier gate cannot qualify later code.
5. Treat absent sufficient public shutdown proof as CAPABILITY_UNAVAILABLE before
   connection/reservation, rather than attempting another native run. Cost: MAIN
   qualification cannot proceed until a sufficient public lifecycle/design is
   established. No method-presence/version/queue-drain inference is accepted.
6. The reviewer did not judge native loading/resume/events/hooks/children.
   Keep them unproven, requiring sufficient capability/design and new authority.
   Cost: no native compatibility or acceptance claim.
7. The reviewer did not judge provider accuracy/live accounting/browser/twelve-role
   behavior. Preserve those excluded/unresolved gates. Cost: MAIN-only evidence
   cannot complete P0-04B or activate operational guards.
8. The reviewer did not independently observe the concurrent package gate,
   remote CI/Security or broader integration readiness. Report author-observed
   local results separately. Cost: local green is not remote certification or
   merge authorization.
9. Test one-byte-overflow HTTP header rejection without sending an already
   rejected body, while the exact-limit case still sends the full1MiB. Cost:
   overflow verifies declared-length early rejection; full-payload behavior is
   independently covered at the exact cap. Test sockets close in finally; the
   production body cap/protocol did not change.

Deferred minor findings: none.

## Next decision

Do not spend a fresh native grant on the known-blocked route. The next technical
decision is a separately reviewed public lifecycle/design that can establish
the required shutdown observation boundary. Neither a Claude update nor another
provider/native attempt has been demonstrated to resolve this causal gap.
The original four-query/eight-read bounded offline proposal is not authorization.
