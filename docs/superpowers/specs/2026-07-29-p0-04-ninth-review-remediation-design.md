# P0-04 Ninth Review Remediation Design

**Status:** Approved for implementation by the operator

**Date:** 2026-07-29

## Context

A fresh read-only review of PR #25 reproduced eight authorization defects in
the native executor command guard. Complete test and mutation gates passed,
which shows that the current suite covers its implementation but lacks the
adversarial semantics below.

The remediation preserves the approved P0-04 architecture: native Claude Code
`PreToolUse` and `PostToolUse` hooks, deterministic local parsing, native
`allow`/`ask`/`deny`, fail-closed unknown syntax, and no pinned Claude Code,
Nori, Node.js, DeepSeek, or other model/runtime version.

## Decision

Every accepted client grammar must consume the complete effective invocation.
Options that execute another program, load an opaque command file, write a
local sink, select an unanalysed script, or hide a nested verb deny unless the
catalogue explicitly models their effect.

Credential reuse is derived from the exact stage that contains and consumes
the literal credential. The aggregate highest-risk stage remains responsible
for the overall decision, but it cannot supply the credential domain, family,
or target class.

## Client-specific closures

- `mongosh` accepts exactly one `--eval` source. Repeated `--eval`, `--file`,
  positional JavaScript, interactive shell/browser behavior, unknown options,
  and unconsumed operands deny.
- `ip` denies `-b` and `-batch`; opaque network-command files are outside the
  deterministic grammar.
- `scp` and `sftp` use separate closed option schemas. Local execution/config
  overrides and SFTP batch files deny. Transfer direction and remote endpoint
  are derived from fully consumed operands.
- `tcpdump` and `tshark` use client-specific closed schemas. A resolved local
  capture sink is a `LOW_RISK_CHANGE` with `FILE_WRITE + ALWAYS_ASK`;
  post-rotate commands, opaque input files, dynamic sinks, and unsupported
  options deny.
- Docker-compatible clients retain their current one-level grammar. `ctr` gets
  a dedicated hierarchical parser for explicitly supported image operations;
  pulls/imports are changes and removals are destructive.
- Git read verbs use closed schemas. `git diff --output` and related local
  sinks are catalogued file writes with `ALWAYS_ASK`; external diff/textconv
  execution and unknown options deny.
- `dmesg` separates display selectors from kernel-control actions.
  `--clear`/`--read-clear` are destructive and console controls are disruptive,
  so they never inherit safe-read authorization.

## Credential binding

Each stage analysis carries whether it is the supported literal credential
consumer. Policy exposes one non-secret `credentialBinding` structure derived
from that stage: domain, family, and target class. `bindingFromResult()` uses
only this structure plus session, tool-use ID, explicit identity, and transport.
It never falls back to aggregate policy metadata.

Changing a curl origin, GitHub repository, database domain, Redis domain, or
other consumer domain therefore requires a fresh native confirmation even when
an earlier stage has higher risk.

## Testing

Each defect receives a real policy-entrypoint regression that is first observed
failing. Tests cover default and `bypassPermissions`, separated/attached option
forms, duplicate aliases, missing values, dynamic operands, command composition,
and source-to-installed fixtures. Security predicates and one-site mutations
are added for the credential-consumer binding and every new parser closure.

The final gate is the full Node test/coverage/mutation runner, repository Python
validators, installed-artifact validation, WSL package validation, and diff
hygiene. No live Claude session or provider credential is required.

## Documentation and versioning

ADR-004, the independent-review record, README, and the existing `0.11.0`
changelog entry record the strengthened behavior and fresh evidence. Review
remediation does not create another version or pin any runtime.

## Acceptance criteria

All eight reproduced commands must no longer receive an authorization weaker
than their real effect. Credential reuse cannot cross the consuming stage's
domain. All new regressions execute against source and installed artifacts,
all registered mutations are killed by matching witnesses, all validation
gates pass, and no raw command or credential enters binding or audit state.
