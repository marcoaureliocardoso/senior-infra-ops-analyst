# P0-04B prior one-client native provenance result

This is a structural record of the already-consumed offline experiment, not an
authorization, main-stage acceptance or full P0-04B result. No transcript, prompt,
reply marker, native session identifier or raw stream is retained here.

Frozen predecessor artifact:
`57fbed5c40cc5994aac492ece213f8c58a333066675b77552dc419e7144b7cb0`
remains STATE_UNPROVEN at the recount-provenance boundary; it is not retroactively
passed by later work.

The separately approved provenance artifact was
`488de64310a64ab3fbd17194812b91a666ecee7db8123b2c8fb5197787ad6632`.
Its one reservation was consumed on 2026-10-23. Result:
M0_M1_PROVENANCE_SUPPORTED,4.521 seconds including isolated cleanup.

| Observation | Total tokens | Max/raw capacity | Percentage | apiUsage |
|---|---:|---:|---:|---|
| M0 | 11 | 200000/200000 | 0 | NULL |
| M1 | 45222 | 200000/200000 | 23 | VALID: input45222/output10/cache-create0/cache-read0 |

Native auto-compaction was enabled for both observations. There were two M0
counting requests, zero M1/M2 counting requests and one generation request
(three HTTP attempts total). Generation-marker association, native-session
binding, isolation and final cleanup were observed. No resume, M2, real provider,
operator state or browser workflow occurred.

The observed public SDK was0.2.173; that is evidence about this experiment, not
a product version pin. The four-stage MAIN-only implementation must establish
its own native history/hook/usage evidence under a new exact-artifact grant.
The existing full acceptance validator still requires its canonical twelve-role
and browser/allow-deny/workflow evidence.
