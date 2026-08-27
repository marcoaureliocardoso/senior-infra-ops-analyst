# P0-06 Guarantee-Separation Independent Review

**Review completed:** 2026-08-27

**Reviewed base:** `bea2c556ef33ac10f36d3adf1af9f4418106763d`

**Reviewed implementation head:** `3737aa328fabf446cbf60a6cbd349a52ceb2f38c`

**Verdict:** Approved. No Critical or Important finding remains.

## Scope and threat boundaries

The independent review covered the schema-v2 authority, tool-proposal, and
output-confidentiality axes; fail and inconclusive precedence; missing-role
handling; denial-audit correlation; contained behavioral-failure continuation;
effect-boundary and resource aborts; prompt and stream deletion; installed
policy preservation; bounded security claims; truthful retention of the two
historical `CANARY_EXPOSED` results; and unchanged package versions.

The reviewer inspected the implementation and tests rather than relying on
commit messages or documentation. The review did not treat deterministic
package behavior as proof of model compliance, did not broaden scope to P0-04B
browser automation, and did not authorize a provider request.

## Findings and remediation

| ID | Finding | Remediation | Status |
|---|---|---|---|
| P006-R1 | Saturating a tool-proposal count above 512 could make it equal a bounded 512-record denial audit and incorrectly permit continuation. | `e1c92c8deea4ca414827d4551194b8f4f0b1c6da` removes metric clamping, rejects out-of-range result metrics, aborts on evidence-count overflow, and retains an exact 512-plus-one regression. | Closed |
| P006-R2 | Equivalent and qualified universal confidentiality claims could evade validation. | `6668f333109d400bc4d41820511ec452fc91b384` covers bounded equivalent forms; `3737aa328fabf446cbf60a6cbd349a52ceb2f38c` adds the exact historical mutation and a same-sentence qualifier bound including transformed output. | Closed |

The final re-review reported no Critical, Important, or Minor finding and
returned `Ready to merge: Yes`. It also confirmed that no authenticated
provider rerun is technically required for these deterministic corrections.

## Reproducible evidence

The focused provider-free gate on the reviewed implementation head ran:

```text
python3 tests/test-prompt-injection-policy.py
python3 tests/test-prompt-injection-install-policy.py
python3 tests/test-prompt-injection-claims.py
python3 tests/test-prompt-injection-live.py
python3 tests/test-prompt-injection-deny-tool.py
python3 tests/test-live-prompt-injection-safety.py
bash -n tests/live-prompt-injection-smoke.sh
bash tests/live-prompt-injection-smoke.sh --self-test
python3 tests/test-architecture-docs.py
python3 tests/test-release-history.py
python3 tests/validate-content.py
```

It passed 3 source-policy, 8 installed-policy, 7 claims, 18 live-parser,
5 deny-hook, 13 harness-safety, 11 architecture, and 42 release-history tests.
Bash syntax, the content-free live parser self-test, and content validation
also passed. No authenticated provider request occurred.

The complete Debian WSL package gate ran with Node.js `v24.17.0` and ended with
`package validation passed`. The command guard passed 288 tests with 100 percent
line, branch, and function coverage and killed all 82 registered mutations.
All P0-06 suites above passed again. Two optional PowerShell checks were skipped
because PowerShell was unavailable in Debian WSL, as documented by the gate.
The canonical staging build and reproducibility check also passed. These
runtime and tool versions describe validation only and are not package pins.

## Accepted residual risks

- Deterministic policy, parser, retention, and control-flow guarantees do not
  guarantee model compliance or universal prompt-injection immunity.
- Output-confidentiality compatibility remains `FAIL` for the two retained
  authenticated observations on commits `65fd95d` and `574c413`; this verdict
  does not relabel those results.
- Runtime compatibility is separately opt-in and runtime-specific. No new
  authenticated matrix was requested or executed for this review.
- Natural-language mutation checks are bounded regression controls, not a
  complete semantic proof over every possible security claim.
- P0-04B browser automation remains outside this delivery.

The verdict is valid for the reviewed implementation head and the documented
provider-free evidence. Any later behavior change requires proportional
revalidation and independent review.
