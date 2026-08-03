# P0-04 Post-RV-88 Remediation Design

<!-- cspell:words pathspec -->

**Date:** 2026-08-03  
**Status:** Remediated through RV-97; final independent verification pending
**Scope:** PR #25, native command guard for executor subagents

## Context

A fresh independent review of PR #25 at `eb0b2bf` confirmed RV-76 through
RV-88 but found four uncovered policy boundaries and two delivery gaps:

1. HTTP redirects can forward unrecognized secret-bearing headers to an
   unaudited origin.
2. Git `add`, `commit`, and `tag` use prefix recognition and misclassify direct
   rewrite forms.
3. Kubernetes `apply --prune` can delete resources while retaining autonomous
   disruptive-change treatment.
4. PowerShell wrappers can load profiles before the analyzed command.
5. CodeQL does not analyze the JavaScript command-guard implementation.
6. The PR description contains stale head and verification evidence.

The existing source and installed gates are green, but their inventory does
not represent these cases. This design closes those gaps without pinning
Claude Code, Nori, Node.js, or the configured model and without adding runtime
dependencies.

A subsequent independent review of the implemented RV-89 through RV-93 head
found four adjacent delivery gaps: curl could still load implicit default
configuration, two platform credential headers were not recognized, the
workflow validator did not prove that CodeQL initialization consumed the
matrix value, and platform-specific test totals were documented ambiguously.
These findings are tracked as RV-94 through RV-97 below.

## Approved scope boundary

Git hooks, clean/process filters, and signing helpers are indirect subprocesses
launched through persistent Git configuration. They are explicitly outside
the command guard's enforcement scope. Their residual risk is documented but
does not force native confirmation for every ordinary Git write.

PowerShell profiles remain in scope. A profile is startup code evaluated by the
same PowerShell process before the analyzed payload, and `-NoProfile` provides
a simple native way to suppress it. The guard therefore requires that option.

The scope exclusion for Git does not excuse direct command semantics. Rewrite
options such as `commit --amend` and `tag --force` are visible in the command
and remain subject to destructive classification.

## Alternatives considered

### 1. Closed operation-specific boundaries

Selected. Keep autonomous behavior only where direct effects are completely
consumed by a finite parser. Reject unresolved redirects and wrapper startup
code, and classify direct destructive options accurately.

### 2. Apply `ALWAYS_ASK` broadly

This would require confirmation for all HTTP headers, Git writes, and
PowerShell wrappers. It is simpler but conflicts with the approved purpose of
`bypassPermissions` as deliberate operational autonomy.

### 3. Inspect effective runtime configuration

Reading Git configuration, PowerShell profiles, redirect chains, and client
state would be environment-dependent, race-prone, and unable to prove the
eventual execution path. This approach is rejected.

## Decision 1: prevent unaudited HTTP redirects

The command guard authorizes one literal HTTP origin. It does not execute a
preflight request and cannot bind an unknown redirect target before the tool
call. Redirect following is therefore outside autonomous HTTP authorization.

- Curl invocations containing `-L`, `--location`, or `--location-trusted` deny
  in every permission mode. Repetition, compact forms, and conflicting forms
  remain fail-closed.
- `Invoke-WebRequest` and `Invoke-RestMethod` require exactly one explicit
  `-MaximumRedirection 0`. Their nonzero and missing forms deny because the
  clients otherwise follow redirects by default.
- The denial explains that the final origin cannot be proven and directs the
  caller to use the final literal URL without redirect following.
- Audit continues to record the one requested literal origin; documentation
  does not describe it as an effective redirect destination.

Curl literal header names are normalized case-insensitively. Names containing
a delimited credential concept such as `authorization`, `auth`, `token`,
`secret`, `credential`, `password`, `passphrase`, `api-key`, `access-key`, or
`private-key` enter the existing `AUTHORIZATION` credential transport. This
covers vendor headers such as `X-Vault-Token`, `X-Auth-Token`, `X-Secret`, and
`X-Access-Key` without reducing the rule to a short exact-name enumeration.
Their values receive the same redaction, first-use approval, binding, and
forbidden-output treatment as other literal authorization credentials.
The bounded taxonomy also includes Azure Functions `X-Functions-Key` and API
Management `Ocp-Apim-Subscription-Key` spellings through delimited
`function-key`, `functions-key`, and `subscription-key` concepts. Nearby
ordinary names such as `X-Function` and `Subscription` remain non-secret.

Clearly non-secret literal headers such as `Accept` and `Content-Type` remain
available. Dynamic header names or values and header-file forms deny. A
PowerShell `-Headers` value is accepted only when the existing literal grammar
can consume it without expressions or file input; redirect denial remains the
cross-origin boundary even when no credential can be derived from the value.

## Decision 2: replace local Git prefix recognition

Separate closed parsers consume every option and operand for `git add`,
`git commit`, and `git tag`. Unknown, repeated, conflicting, dynamic, file-fed,
interactive, editor-dependent, or unconsumed forms deny.

### Git add

The parser supports literal paths, the `--` separator, and the finite scope
options `-A`/`--all`, `-u`/`--update`, `-N`/`--intent-to-add`, and
`--renormalize`. It requires at least one literal path or explicit scope option.
Interactive/edit forms and `--pathspec-from-file` deny. Accepted forms remain
`LOW_RISK_CHANGE`.

### Git commit

The parser requires one or more bounded literal `-m`/`--message` values and
supports the finite flags `-a`/`--all`, `--allow-empty`,
`--allow-empty-message`, `--no-verify`, `-s`/`--signoff`, and an optional
literal `-S`/`--gpg-sign` selector. Literal `--author` and `--date` metadata are
accepted once. Message files, editor-dependent forms, fixup/squash modes,
configuration overrides, and unknown options deny.

An otherwise valid commit containing `--amend` is `DESTRUCTIVE`. Other accepted
commit forms remain `LOW_RISK_CHANGE`. Hooks and configured signers are covered
by the approved out-of-scope boundary rather than by the risk decision.

### Git tag

The parser accepts one literal tag name, an optional literal object, lightweight
creation, annotated `-a`/`--annotate`, signed `-s`/`--sign`, one literal
`-u`/`--local-user`, bounded literal `-m`/`--message` values, and `--no-sign`.
Deletion through `-d`/`--delete` and replacement through `-f`/`--force` are
`DESTRUCTIVE`. Ordinary creation remains `LOW_RISK_CHANGE`. Listing/query
forms, message files, dynamic operands, conflicting signing modes, and unknown
options deny. Configured signing helpers remain outside enforcement scope.

All accepted Git operations bind target data derived from their parsed literal
operands rather than the final raw token.

## Decision 3: classify Kubernetes prune as destructive

The closed Kubernetes option grammar models prune as a boolean singleton and
uses it in risk derivation. An enabled `--prune` on `apply` produces `DESTRUCTIVE` for
both `kubectl` and `k3s kubectl`, so native confirmation is mandatory in every
permission mode. The operation remains authorizable and therefore returns
`ask`, not `deny`.

Disabled prune remains an ordinary disruptive apply. Malformed, repeated, or
unconsumed prune forms deny under the closed option grammar. Existing explicit
context, namespace, file target, and selector binding remains required.

## Decision 4: require profile-free PowerShell wrappers

The outer Bash lexer continues to preserve the complete wrapper composition.
For both `pwsh` and `powershell`, the wrapper grammar requires:

- exactly one case-insensitive canonical `-NoProfile` before `-Command`;
- at most one optional canonical `-NonInteractive`;
- only canonical `-NoLogo`, `-Sta`, or `-Mta` auxiliary options;
- no duplicate options and no simultaneous `-Sta` plus `-Mta`;
- exactly one `-Command` and one literal payload token;
- no outer operator, redirect, or unconsumed argument.

Abbreviations such as `-NoLog` deny even if a client version currently accepts
them. Missing `-NoProfile` produces actionable denial guidance telling the
caller to retry with `-NoProfile`. This boundary does not claim to neutralize
automatic module loading or every behavior internal to an accepted cmdlet.

## Decision 5: extend static security analysis

The CodeQL job matrix contains both `python` and `javascript-typescript`.
Existing action references, permissions, timeouts, and ShellCheck remain
unchanged. Repository validation requires `security.yml`, the exact
two-language-only matrix under `jobs.codeql.strategy`, and exactly one direct
and unconditional CodeQL `init` plus `analyze` step in that same job. The init
step has exactly one direct `with.languages: ${{ matrix.language }}` binding.
Matrix `include`/`exclude`, duplicate keys, decoy jobs, scalar lookalikes,
step/job `if`, and step/job `continue-on-error` are rejected so later edits
cannot silently remove JavaScript coverage, hard-code the initialized
language, skip a security step, or make its failure non-blocking.

## Decision 6: neutralize implicit curl configuration

Curl may load user or system default configuration before applying visible
arguments. The guard cannot audit that external state atomically. Every curl
form eligible for authorization therefore requires exactly one literal `-q`
or `--disable` as its first argument. Missing, late, repeated, negated, or
compact spellings deny with `DENY_CURL_DEFAULT_CONFIG` and operator guidance.
The accepted option is still consumed by the closed client grammar.

This rule applies before redirect, method, credential, sink, and target
classification. It prevents an implicit configuration file from adding a
redirect, body, upload, secret header, method, or output sink that is absent
from the audited command. It does not inspect or depend on the contents of
the operator's curl configuration.

## Policy and error behavior

The risk taxonomy and native decision matrix remain unchanged:

- fully understood destructive operations return `ask` in every mode;
- accepted low-risk changes ask normally and may allow in
  `bypassPermissions`;
- unsupported or inconclusive grammar returns `deny`;
- a credential-bearing direct request uses existing first-use and binding
  rules;
- no raw command or credential is added to audit or operator-visible output.

New denial guidance is specific to redirects, missing `-NoProfile`, and closed
Git forms. It explains what was rejected and how to produce a supported command
without echoing the original command or secret. The implementation exposes
distinct stable reason codes for these three classes.

## Executable evidence

Every production behavior change follows an observed RED/GREEN cycle through
the real policy entrypoint.

1. A two-origin loopback fixture proves that curl redirect forwarding cannot
   receive autonomous authorization. It uses only a synthetic credential.
2. Curl and PowerShell HTTP matrices cover missing, zero, nonzero, repeated,
   compact, and malformed redirect controls; safe and secret-bearing headers;
   dynamic expressions; and file inputs.
3. Separate Git matrices cover accepted operands, exact option arity,
   duplication, conflicts, bounds, rewrite flags, deletion, signing spellings,
   interactive/file-fed forms, and unknown options.
4. Kubernetes fixtures cover `apply --prune` for kubectl and k3s in normal and
   bypass modes.
5. PowerShell wrapper fixtures cover both executables, missing and duplicate
   `-NoProfile`, canonical options, abbreviations, conflicts, and outer arity.
6. A workflow validator requires both CodeQL languages, the security workflow,
   and the exact matrix-to-initialization binding.
7. A loopback fixture demonstrates that a synthetic `.curlrc` body changes a
   visible GET into POST without `-q`, while the first-argument `-q` form
   remains the audited GET.
8. Stable RV-94 and RV-95 fixtures exercise source and installed policy for
   missing, late, repeated, negated, short and long curl configuration controls
   plus platform-key and benign adjacent headers.

Each security boundary has a stable review-regression ID, source and installed
corpus fixture, exact one-site typed mutation where runtime behavior changes,
and a matching witness. Coverage inventory and documentation counts are
derived from executable registries rather than hand-authored labels.

## Documentation and delivery

The remediation updates README, CHANGELOG, ADR-004, the independent-review
ledger, architecture/spec indexes when required, and the PR description. These
documents record:

- requested versus effective HTTP origin semantics;
- the redirect and profile-free wrapper boundaries;
- direct Git semantics and the explicit residual-risk exclusion for indirect
  Git subprocesses;
- destructive Kubernetes prune behavior;
- JavaScript CodeQL coverage;
- fresh head, test, mutation, and installed-fixture evidence.

Version `0.11.0` remains unchanged because it has not been released. No Claude
Code, Nori, Node.js, or model version is pinned, and no new runtime dependency
is introduced.

## Verification and completion

Completion requires:

1. the focused RED/GREEN suites;
2. the full Node.js gate with 100 percent critical line, function, and branch
   coverage and all typed mutations killed;
3. install-policy and source-to-installed byte-equivalence validation;
4. all review fixtures executed in the installed corpus;
5. the full Debian/WSL package gate;
6. Markdown, spelling, schema, workflow, and diff checks;
7. a fresh independent adversarial review of the final head;
8. a pushed PR #25 head with all required GitHub checks green and an updated
   description.

Merge is not part of this remediation unless separately requested.
