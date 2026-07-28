# P0-04 Third Review Remediation Design

## Status

Approved for implementation by the operator on 2026-07-28 through the
instruction to correct every finding from the latest PR #25 review.

## Problem

The published command guard passes its structural coverage and mutation gates,
but four credential-boundary behaviors remain unsafe:

- catalogued credential spellings can escape literal classification;
- `OPS_CREDENTIAL_IDENTITY` is mistaken for a credential transport;
- curl route and TLS overrides do not participate in the approved domain;
- kubectl accepts endpoint and credential overrides outside a closed schema.

These gaps let a bounded read execute without the required first-use prompt or
let an active approval be reused with a different transport or effective
destination.

## Considered approaches

### Extend the current regular expressions only

Add every currently known spelling to `redaction.mjs`. This is small but keeps
credential semantics separate from the client parsers and is likely to regress
when another compact or equals-attached form is added. Rejected.

### Bind every route modifier

Store proxy, resolved address, TLS mode, Kubernetes server, certificate, user,
and impersonation details in binding state. This preserves more client
flexibility but expands sensitive state and makes destination equivalence hard
to prove statically. Deferred until a concrete operational need justifies it.

### Client-aligned credentials with fail-closed routes

Derive exact lexical patterns from each client's accepted option schema, exclude
the non-secret identity marker, and reject route or trust overrides that cannot
be represented by the current binding. Apply a closed kubectl global option
schema. Selected because it matches the finite-catalogue architecture, retains
raw-span redaction before output, and keeps the approval record auditable.

## Design

### Credential classification

`OPS_CREDENTIAL_IDENTITY` is metadata only and never produces a sensitive span.
The classifier must recognize all credential-bearing forms already accepted by
the catalogue, including:

- curl `--oauth2-bearer`, separated and attached `-u`, and `--user=`;
- every non-empty `Authorization` header scheme;
- Redis `--pass`, `--pass=`, attached `-a`, and separated `-a`;
- the existing variable, query, cookie, URI, and provider transports.

The first actual credential span determines the binding transport. Every
recognized literal asks on first use in all permission modes and remains absent
from responses, audit data, and structural fingerprints.

### HTTP routing

The current binding uses the URL origin as its credential domain. Therefore
curl options that can change routing or disable peer verification are not
catalogued:

- `--resolve`;
- `--proxy` and `-x`;
- `--insecure` and `-k`.

Client certificate and key references remain supported only with the literal
URL route and normal server verification. Alternative CA files, authenticated
redirects, and peer-verification bypasses remain denied.

### Kubernetes routing

Kubectl and `k3s kubectl` use a closed schema for global options and the options
needed by each supported verb. The guard denies options that change server,
credentials, executable authentication, TLS trust, configuration files,
impersonation, or plugin behavior, including their separated and equals forms.

The safe environment remains the explicit `--context` plus optional namespace.
Because endpoint overrides are denied, that context is again an honest binding
for the selected cluster configuration. Finite output constraints for logs,
watch, raw endpoints, and chunk size remain unchanged.

### Failure behavior

Unsupported credential, route, TLS, Kubernetes global, or malformed option
forms return the existing fail-closed `DENY_UNKNOWN_COMMAND`. No raw command or
credential is included in the reason.

## Test design

Regression tests exercise real `analyzeCommand` and hook binding behavior:

- every newly catalogued credential spelling asks and is redacted;
- the identity marker alone is not a credential;
- Authorization approval cannot be reused as Cookie or Basic Auth;
- route and TLS overrides deny before and after an active binding;
- Kubernetes server, token, certificate, key, TLS, impersonation, and plugin
  overrides deny in both permission modes;
- existing explicit context, namespace, bounded reads, client certificates,
  literal HTTP bodies, and provider profiles retain their expected behavior.

Each regression is observed failing before production changes. The final gate
uses a Linux Node runtime that supports the native test coverage flags required
by `tests/run-command-guard-tests.mjs`, then executes
`tests/validate-package.sh` unchanged.

## Documentation impact

ADR-004, the independent-review verdict, changelog, README or execution
protocol are updated only where their current claims would otherwise overstate
the closed schemas or credential binding. The package version remains 0.11.0
because PR #25 is unreleased and this is corrective work within the same
release candidate.
