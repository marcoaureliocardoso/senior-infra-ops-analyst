# Redis Binding and TLS Boundary Design

## Context

The command guard currently accepts Redis options while locating a command
verb without proving that every option is modelled. It also records only the
host as the Redis environment. Consequently, an approved literal credential
can be reused after adding `--insecure` or changing port, database, or ACL user.

## Decision

Use a closed minimal `redis-cli` option schema. Accept only the existing
literal host, port, database, password, and user selectors plus the `--tls`
flag. Reject compact route selectors, repeated singleton aliases, unknown
options, URI/socket routing, cluster redirection, trust overrides, client
certificate inputs, SNI overrides, insecure verification, stdin argument
sources, repeat/special modes, and configuration-driven behavior.

Represent the effective Redis environment as a canonical non-secret string
containing transport, host, port, database, and user. Defaults are explicit:
plain TCP, port `6379`, database `0`, and user `default`. A change to any field
therefore creates a different approval domain. The password remains excluded.

## Data Flow

1. The Redis branch validates the complete option list before locating the
   command verb.
2. Accepted selectors are parsed once after duplicate rejection.
3. Literal and bounded values form a canonical environment.
4. Policy, action identity, audit, pending binding, and active-binding lookup
   all consume that same environment without separate Redis-specific state.
5. Prohibited or unconsumed options fail closed as `DENY_UNKNOWN_COMMAND` with
   the existing operator-visible guidance.

## Compatibility

Plain TCP and system-trust TLS remain operational. Advanced TLS configurations
are denied until a future version explicitly models file provenance, SNI,
client identity, and trust binding. Claude Code, Nori, Node.js, and model
versions remain capability observations rather than pins.

## Verification

- Witness RED lifecycle tests for TLS-to-insecure reuse and changes to port,
  database, and user under one approval.
- Test accepted default and explicit canonical environments.
- Test every rejected Redis route, trust, credential-file, stdin, repeat,
  cluster, and unknown-option family in normal and bypass modes.
- Add stable review fixtures and run them against source and installed policy.
- Retain 100 percent critical line/function/branch coverage and the complete
  mutation, package, documentation, PowerShell, and hygiene gates.
