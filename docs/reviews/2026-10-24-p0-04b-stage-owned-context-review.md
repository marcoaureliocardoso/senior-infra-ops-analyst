# Stage-owned SDK context: independent review and author correction

Reviewed range: 9e6eaf623bd46777f3f167817a4f9ed0f365ceb6 through
7c65f29deeb257bbd5a65ee6216e2586c2d3ce4e. One fresh-context independent
reviewer read the whole change, approved design/plan and ledger rulings. Review
was read-only, with no native/provider invocation. The reviewer independently
passed 35 contract/SDK/gateway methods without skips. Verdict: not ready; two
Important findings, no Critical or Minor findings.

1. The actual public SDK disconnect closes Query by setting its closed state,
   cancelling its reader, then closing the transport. An entirely in-memory
   public ClaudeSDKClient transport emitted a failing task notification during
   close; the adapter still returned QUALIFIED/NONE. Application-consumer lifetime
   alone cannot establish transport-shutdown observability.
2. A sticky reset/error received on connection did not prevent the before read
   and query. A synthetic connection reset produced connect/consumer/before/query/
   close even though final acceptance correctly failed.

The single author TDD correction pass reproduced both findings before editing.
It now gates every pre-query asynchronous boundary on observed state. It also
fails closed BEFORE connecting any actual SDK client, including subclasses:
no sufficient public shutdown-observation protocol is currently qualified.
Pure options/parser construction remains testable; method presence or a version
number cannot qualify the native lifecycle. The CLI refuses native qualification
before consuming a reservation or launching a namespace. There is no override.
The memory-only custom transport is a regression fixture, not a production
transport replacement. No private SDK state/control, queue-drain inference,
extra observer, warm-up or native retry was introduced.

This correction does NOT establish native compatibility. Native preparation is
CAPABILITY_UNAVAILABLE until a sufficient public lifecycle is established under
a separately approved design/evidence route. Updating Claude alone is not a
demonstrated remedy. Do not request or spend a native grant on the known-blocked
profile. The original four-stage budget remains a proposal, not permission.

No second review is requested under the approved inline method. Author tests and
the corrected immutable package gate are recorded in validation notes, separately
from the review of 7c65f29 and its concurrently running original gate.

## Behaviors the reviewer did not judge

- Actual native project loading/resume/events/hooks/children: prohibited in the
  review. Ruling: keep them unproven and do not run without a new sufficient
  capability/design and grant. Cost: no native compatibility or acceptance claim.
- Provider accounting/live limits, operational browser and twelve-role acceptance:
  explicitly excluded/unresolved. Ruling: preserve those gates. Cost: main-only
  evidence cannot close P0-04B or activate operational guards.
- Concurrent package gate, remote CI/Security and broader merge readiness: not
  independently observed. Ruling: report author-observed package results separately
  and retain remote/integration gates. Cost: local green is not remote certification.

Deferred minor findings: none.

The corrected immutable full gate subsequently passed on8d1b596 in1,461.331s.
This is author-observed package verification, not a second independent review or
native qualification; see the [final handoff](2026-10-24-p0-04b-stage-owned-context-handoff.md).
