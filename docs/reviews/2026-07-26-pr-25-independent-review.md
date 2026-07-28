# PR #25 Independent Review Verdict

**Date:** 2026-07-26

**Scope:** P0-04 native command guard, PR #25

**Initial reviewed commit:** `0f03bb999afc7c6f878eb28b770357cdb06ddc88`

**Final reviewed commit:** `7c2e32751001adfbf8bdc1036465d7ec2bdbfa1a`

**Previous verdict:** Ready to merge with RV-11 accepted as a temporary
exception; superseded by the 2026-07-28 re-review below

**Re-review base commit:** `99800545ba998931a022855a962f0357a86a0d0e`

**Current verdict:** Changes required. Remediation is implemented in the PR
worktree, but merge authorization requires a fresh independent review of the
new head. RV-11 remains an accepted temporary exception.

**Remediation design:**
[P0-04 review remediation](../superpowers/specs/2026-07-26-p0-04-review-remediation-design.md)

## Initial verdict

The implementation establishes a useful deterministic enforcement boundary,
but it is not safe to merge in its reviewed form. The source suite reported 62
active passing tests, one intentional skip, 100 percent structural coverage,
and 11 killed mutations. All nine GitHub checks were green. Those results do
not cover several executable semantic paths that can be incorrectly allowed,
nor do they prove equivalence between source and installed behavior.

The blockers below were independently reproduced. Each requires a failing
regression fixture before its correction. The verdict remains open until the
source validator, installed artifact, and applicable live smoke have passed
the remediated gates and a new independent review records no blocking finding.

## Final independent disposition

The second independent review of the final head found no remaining blocker. RV-01
through RV-10 and RV-12 through RV-17 are resolved. RV-11 remains an explicitly
accepted temporary exception: normal provider credentials may enter the live
smoke process only after the dedicated acknowledgement, while provider egress
remains open and is reported as residual risk.

The final independent review executed 31 targeted cases and the complete
suite of 87 active tests with one intentional mutation-only skip. It observed
100 percent line, function, and branch coverage, killed all 11 security
mutations, validated all 11 installed-artifact checks, executed the same
27-fixture adversarial corpus against source and installed forms, and passed
the formatting check. The reviewer also reproduced the corrected PostToolUse
no-op behavior, sensitive process and AWS classifications, the real audit
failure path, and the executable RV-12 fixture linkage.

## Blocking findings

| ID | Finding | Reproduced behavior | Required outcome | Status |
|---|---|---|---|---|
| RV-01 | Hook bootstrap can fail open | Native hook infrastructure errors outside the validator do not reliably block execution | A launcher must convert missing runtime, missing artifact, validator crash, malformed output, and internal deadline failure into native blocking exit `2` | Resolved |
| RV-02 | PowerShell wrapper drops outer composition | Only the argument after `-Command` is analyzed; outer operators, redirections, and remaining arguments can escape analysis | Parse the complete outer command and accept only one fully consumed, unambiguous wrapper invocation | Resolved |
| RV-03 | Arbitrary environment assignments can replace execution semantics | Generic `NAME=value` prefixes permit control variables such as `PATH`, `LD_PRELOAD`, and `GIT_EXTERNAL_DIFF` | Permit only explicitly modelled non-control assignments; deny unknown and execution-control variables | Resolved |
| RV-04 | HTTP side effects and file sinks are underestimated | Body, upload, and output options can be classified as safe read-only operations | Use client-specific parsers that derive effective method, request body, upload, redirect, authentication, and every local sink | Resolved |
| RV-05 | Protected credential flow accepts sequence instead of pipe | A decryptor followed by `;` can print a secret and still be accepted as a protected consumer flow | Require exactly one immediate `|` edge from the decryptor to one direct catalogued consumer and reject every other edge or sink | Resolved |
| RV-06 | Credential reuse is not bound to prior operator approval | A literal is accepted from its current generic consumer without trusted session, domain, identity, or transport state | Activate only non-secret binding state after a matching operator-approved tool use and require the same binding for reuse | Resolved |
| RV-07 | Redaction and audit identity depend on raw secret material | Several credential forms survive redaction and different secret values alter the command fingerprint | Detect secrets with parser-aware schemas and remove raw-command or secret-derived fingerprints from decisions and audit | Resolved |
| RV-08 | Generic read families expose secrets or perform mutations | Examples include secret reads, environment-bearing process listings, journal vacuum, socket destruction, and broad inspect operations | Replace generic read labels with executable-specific argument schemas, sensitive-output rules, and explicit mutating variants | Resolved |
| RV-09 | SQL classification relies on an incomplete keyword blacklist | Side-effecting functions can execute inside statements classified as reads | Authorize only a narrow parsed read subset and deny or ask for unproved functions, clauses, and multi-statements | Resolved |
| RV-10 | Destructive Git push forms are underestimated | Mirror, prune, deletion refspecs, and force refspecs can receive low-risk autonomous treatment | Parse push refspecs and destructive flags explicitly; destructive variants always require an exact operator decision | Resolved |
| RV-11 | Live smoke exposes normal provider credentials | The harness imports normal credentials without provider-egress isolation | Retain them only as an accepted temporary exception with explicit opt-in, acknowledgement, Bash environment-use denial, isolation, and residual-risk reporting | Accepted temporary exception |
| RV-12 | Coverage manifest fabricates labels instead of proving fixture execution | Generated positive and negative labels are not linked to executed cases | Register stable IDs on executable fixtures and fail when a declared case was not executed | Resolved |
| RV-13 | Installed validation proves paths, not artifact equivalence | Installed modules can differ from source while path checks still pass | Compare installed module content with source and execute the same adversarial fixture corpus against both | Resolved |
| RV-14 | Aggregate result hides relevant stages | Only one highest-risk stage is retained, including when later stages have equal risk | Emit bounded, redacted per-stage findings and aggregate all policy-relevant edges and sinks | Resolved |
| RV-15 | Event schema is too rigid for harmless runtime evolution | Unknown observational metadata and future effort values can reject an otherwise understood event | Keep execution-affecting input strict while tolerating bounded observational top-level extensions conservatively | Resolved |
| RV-16 | External side effects can be autonomous | GitHub comments, issues, and similar externally persisted actions can be allowed in bypass mode | Mark externally persisted effects explicitly and always return `ask` | Resolved |
| RV-17 | Formatting gate reports a trailing blank line | `git diff --check` reports `tests/command-guard/helpers.mjs` | Remove the whitespace defect and retain the diff check as a gate | Resolved |

## Accepted temporary exception for live smoke

The operator explicitly approved retaining normal Claude provider credentials
in the opt-in live smoke for the current remediation. This is an accepted
temporary residual risk, not a closed finding and not evidence that the smoke
is safe for arbitrary prompts or commands.

The minimum compensating controls are:

- live execution remains disabled unless separately and explicitly requested;
- a dedicated acknowledgement confirms that normal provider credentials will
  enter the isolated model process;
- the command guard denies Bash references to provider-control-plane
  credential variables and denies environment-dump or equivalent discovery
  forms;
- the test home and writable paths remain isolated and runtime mounts remain
  read-only where supported;
- live targets remain synthetic, loopback, or disposable;
- output and retained artifacts are scanned for synthetic markers and known
  provider variable names without reading or comparing the provider values;
- test output states that provider egress remains available and that the
  controls reduce, but do not eliminate, exfiltration risk.

Disposable credentials or provider-egress allowlisting remain the preferred
future replacement. They are not prerequisites for this remediation because
the operator accepted the temporary exception above.

## Closure criteria

The final independent review verified every closure criterion below for the
final head, subject to the accepted RV-11 exception:

1. Every open blocker has an executable red regression and a reviewed fix.
2. The complete source suite, branch coverage gate, mutation gate, content
   validation, and formatting checks pass.
3. The installed Nori artifact is content-equivalent for the security-critical
   modules and passes the same adversarial corpus.
4. Launcher failure paths are demonstrated to block before execution.
5. The explicitly acknowledged live smoke passes under the approved exception
   and reports its residual risk.
6. ADR-004 and user-facing documentation describe the implemented behavior,
   not the superseded behavior.
7. A new independent reviewer inspects the patch and records the final
   disposition of every finding.

This authorization was valid for the reviewed commit at the time. It is
superseded by the 2026-07-28 re-review below; repository integration now
requires another independent disposition.

## Verified remediation evidence

The final independent reviewer inspected the remediated head and reproduced
the following evidence:

- Stable fixture IDs execute every reproduced regression and fail on orphan,
  undeclared, duplicate, or unexecuted cases.
- The source gate passes 87 active tests plus one intentional mutation-only
  skip, 100 percent line/function/branch coverage, four deterministic property
  seeds, and 11 killed security mutations.
- Source-to-installed validation byte-compares every security-critical
  launcher, entrypoint, and module, then executes the same 27-fixture review
  corpus against both forms.
- Launcher tests prove missing runtime, missing artifact, timeout, crash,
  malformed output, and unexpected stdout block before command execution.
- The complete package gate, architecture tests, static smoke contract,
  installed validation, and `git diff --check` pass.
- The explicitly acknowledged Debian WSL2 live smoke passes and reports that
  normal provider credentials entered the Claude process while provider egress
  remained open. This is evidence for the compensating controls, not closure
  of RV-11.

## 2026-07-28 re-review disposition

A later review of PR head `9980054` reproduced six semantic gaps that were not
represented by the green suite. PowerShell expression evaluation also escaped
the guard in normal mode, so line and branch coverage did not establish the
claimed authorization boundary. The previous merge authorization is therefore
withdrawn.

The remediation adds executable regressions and tightens the finite grammar.
The statuses below mean the local implementation satisfies the reproduced
case; they do not replace independent verification of the resulting head.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-03 | Execution-control assignments remained allowlisted | `GIT_ASKPASS` and an arbitrary `KUBECONFIG` could introduce external helpers | Restrict in-command assignments to credential transports and the named AWS profile reference | Remediated; independent verification pending |
| RV-04 | Curl inline file sources escaped detection | `--data=@file` and related attached forms were autonomous in bypass mode | Parse separated, equals-attached, and compact curl values and deny every local request-file source | Remediated; independent verification pending |
| RV-08 | Raw Kubernetes API bypassed sensitive-resource detection | `kubectl get --raw=.../secrets/...` was a narrow read | Deny raw API endpoints before resource classification | Remediated; independent verification pending |
| RV-18 | PowerShell arguments evaluated nested commands | A read cmdlet containing `(Remove-Item ...)` was allowed in every mode | Reject unquoted expression, type, and call delimiters before token classification | Remediated; independent verification pending |
| RV-19 | SSH option denylist omitted executable hooks | `KnownHostsCommand` executed a local helper while the remote read was allowed | Replace the denylist with a closed literal transport-option schema | Remediated; independent verification pending |
| RV-20 | Kubernetes streams were not finite | `logs --follow`, `get --watch`, and disabled pagination were allowed | Deny enabled follow/watch/raw streams and invalid or zero chunk sizes | Remediated; independent verification pending |

The executable fixture ledger now includes the new stable IDs, and the direct
security suite covers spelling and boundary variants. A new independent
reviewer must inspect the patch, reproduce the cases against source and
installed form, run the complete gates, and record the resulting commit and
verdict before merge.
