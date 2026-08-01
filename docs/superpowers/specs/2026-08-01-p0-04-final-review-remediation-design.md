# P0-04 Final Review Remediation Design

## Context
The tenth independent review of PR #25 found three gaps that the existing 204-test, 100%-coverage, and 46-mutation gates did not expose:

1. literal credential ownership is assigned to the last composition stage instead of the stage containing the sensitive span;
2. accepted `scp` and `sftp` endpoint selectors do not participate in the canonical credential domain and audit identity;
3. packet-capture stdout and duplicate option aliases are not modelled precisely.

The command guard remains fail-closed, dependency-free, compatible with the JavaScript runtime capabilities already required by its launcher, and independent of fixed Claude Code, Nori, Node.js, or model versions.

## Decision 1: bind literal credentials to source spans
`buildComposition` will retain an in-memory source interval for every stage. The interval covers every lexical token belonging to that stage, including redirection operands, and is never included in the response, binding store, or audit record.

`classifyCredentials` will map every sensitive source span to exactly one stage interval. A literal is accepted for further analysis only when all detected spans resolve to the same stage. No match or spans distributed over multiple stages produce `DENY_UNKNOWN_CREDENTIAL_CONSUMER`. The selected stage must itself be a catalogued credential consumer; a later stage can no longer lend consumer status or domain identity to an earlier one.

Credential binding continues to store only non-secret domain, family, target class, identity, transport, session, and expiry. The literal and raw command remain excluded.

## Decision 2: canonicalize the complete SSH endpoint
The remote-transfer parser will normalize endpoint-affecting selectors into a single structure:

- remote user from `user@host`, URI userinfo, `-l`, or `-o User`;
- port from URI, `-P`, or `-o Port`, defaulting to 22;
- jump route from `-J` or `-o ProxyJump`;
- literal host from the remote operand.

Equivalent aliases are one singleton option group. Repetition, conflict, an absent explicit user, dynamic values, or unsupported SSH options deny the command. The canonical environment is `ssh://user@host:port` with a percent-encoded `?via=` suffix when a jump route is present. This environment becomes both the credential-reuse domain and the non-secret audit identity.

Options that can select local executors, opaque configuration, routing commands, loaders, or plugins remain denied. Identity-file selection is accepted only as a literal protected-file reference and does not replace endpoint identity.

## Decision 3: distinguish packet stdout from file persistence
`tcpdump` and `tshark` option aliases will be grouped by semantic role. A second interface, count, snapshot length, or sink selector denies the command even when a different alias spelling is used.

`-w -` is modelled as packet data written to stdout, not as a file named `-`. It remains `SAFE_READ_ONLY` but carries `SENSITIVE_OUTPUT`, `RESOURCE_INTENSIVE`, and `ALWAYS_ASK`, with target `<interface> -> stdout:pcap`. A literal filesystem sink remains `LOW_RISK_CHANGE` with `FILE_WRITE` and `ALWAYS_ASK`. Dynamic, home-relative, repeated, or post-processing sinks remain denied.

## Verification architecture
Each decision is protected at four levels:

1. focused behavioral tests that are observed failing before production changes;
2. independent-review regression fixtures with literal expected decisions and identities;
3. security predicate inventory plus mutation witnesses that fail if the new guard branch is weakened;
4. the complete command-guard gate, repository validators, WSL package validation, and spell check.

The review ledger, ADR-004, README, CHANGELOG, and coverage inventory will describe the resulting behavior. Version `0.11.0` remains unchanged because this is remediation within the unreleased PR scope.
