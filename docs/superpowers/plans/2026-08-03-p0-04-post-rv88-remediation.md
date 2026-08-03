# P0-04 Post-RV-88 Remediation Implementation Plan

<!-- cspell:words hashtable nolog nologo subtests marcoaureliocardoso -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four command-authorization findings discovered after RV-88, extend JavaScript security analysis, and refresh PR #25 evidence without reducing approved operational autonomy.

**Architecture:** Extend the existing closed parsers and typed mutation registry rather than adding another enforcement layer. HTTP redirects and profile-loading wrappers fail closed, local Git direct semantics receive dedicated parsers, Kubernetes prune becomes destructive, and indirect Git subprocesses remain an explicitly documented residual risk.

**Tech Stack:** ECMAScript modules, Node.js native test runner and coverage, Python and Bash repository validators, GitHub Actions CodeQL, Debian/WSL installed-package validation, Markdown ADRs and review ledger.

## Global Constraints

- Keep version `0.11.0`; it has not been released.
- Do not pin Claude Code, Nori, Node.js, or the configured model.
- Do not add a runtime dependency or background service.
- Preserve `bypassPermissions` autonomy for fully parsed non-destructive work.
- Git hooks, filters, and signing helpers are outside enforcement scope and must be documented as residual risk.
- Require `-NoProfile` because PowerShell profile code executes before the analyzed payload in the accepted wrapper process.
- Unknown, repeated, conflicting, dynamic, file-fed, interactive, or unconsumed forms deny.
- Never persist or echo raw commands or credentials.
- Every behavior change must be observed RED before production code changes and GREEN afterward.
- Every authorized curl form must place exactly one literal `-q` or
  `--disable` first; implicit client configuration is not audited.

---

## File structure and responsibilities

- `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
  owns HTTP, Git, and Kubernetes closed grammars and risk results.
- `skills/command-driven-operations/scripts/command-guard/policy.mjs` owns
  PowerShell wrapper validation, reason codes, guidance, and native decisions.
- `skills/command-driven-operations/scripts/command-guard/redaction.mjs` owns
  literal secret-header recognition and redaction spans.
- `tests/command-guard/security-regressions.test.mjs` owns direct adversarial
  policy-entrypoint coverage.
- `tests/command-guard/branches.test.mjs` owns accepted finite grammar branches.
- `tests/command-guard/review-regression-fixtures.mjs` is the executable review
  ledger used by source and installed artifacts.
- `tests/command-guard/mutations.mjs` and `mutation-witnesses.mjs` prove each
  security predicate with an exact one-site mutant.
- `tests/test-ci-workflows.py` will own executable workflow-language checks.
- `.github/workflows/security.yml` owns CodeQL language coverage.
- README, CHANGELOG, ADR-004, the post-RV-88 spec, and the independent-review
  ledger own operator and architecture statements.

---

### Task 1: Fail closed on unaudited HTTP redirects and recognize secret headers

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/credential-flow.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-witnesses.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/redaction.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `tests/loopback-http-fixture.py`
- Modify: `tests/test-loopback-http-fixture.py`

**Interfaces:**
- Consumes: `lookupFamily(stage, context)`, `detectSensitiveSpans(command)`,
  existing `AUTHORIZATION` credential transport, and native deny responses.
- Produces: catalog results may contain
  `{ denyReasonCode: 'DENY_UNBOUND_HTTP_REDIRECT' }`; secret-like curl headers
  produce `AUTHORIZATION` spans; autonomous HTTP has exactly one literal origin.

- [x] **Step 1: Add failing policy tests for redirects and secret headers**

Add a focused test containing these assertions:

```javascript
for (const command of [
  'curl -L https://origin.example.invalid/start',
  'curl --location https://origin.example.invalid/start',
  'curl --location-trusted https://origin.example.invalid/start',
  'curl -LsS https://origin.example.invalid/start',
  'curl -L -L https://origin.example.invalid/start',
  'Invoke-WebRequest -Uri https://origin.example.invalid/start',
  'Invoke-RestMethod -Uri https://origin.example.invalid/start -MaximumRedirection 1',
]) {
  for (const mode of ['default', 'bypassPermissions']) {
    const result = analyze(command, mode);
    assert.equal(result.decision, 'deny', `${mode}: ${command}`);
    assert.equal(result.reasonCode, 'DENY_UNBOUND_HTTP_REDIRECT', command);
  }
}

for (const client of ['Invoke-WebRequest', 'Invoke-RestMethod']) {
  assert.equal(analyze(`${client} -Uri https://api.example.invalid/health -MaximumRedirection 0`).decision, 'allow');
}

for (const name of ['X-Vault-Token', 'X-Auth-Token', 'X-Secret', 'X-Access-Key']) {
  const result = analyze(`curl -H "${name}: SYNTH_SECRET_rv89" https://api.example.invalid/health`);
  assert.equal(result.decision, 'ask', name);
  assert.equal(result.credential.transport, 'AUTHORIZATION', name);
  assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_rv89/u, name);
}
```

Also assert that literal `Accept` and `Content-Type` headers remain accepted;
`-H @headers.txt`, dynamic names/values, repeated redirect controls, and
nonzero, negative, abbreviated, or malformed PowerShell redirect values deny.
Exercise separated and `=` spellings of the canonical PowerShell option. For
PowerShell `-Headers`, cover the existing literal `Name: value` spelling with
an ordinary header and a secret-bearing header, then deny expression,
variable, and file-derived values.

- [x] **Step 2: Add a failing two-origin loopback regression**

Extend the local fixture with two listeners. The first returns `302 Location`
to the second and the second records request headers. Invoke the real curl
client only with `SYNTH_SECRET_rv89`; assert the client demonstrates the threat
fixture, while the guard denies the same command before execution. Keep the
fixture loopback-only and never import provider credentials.

- [x] **Step 3: Run the focused RED suite**

Run:

```bash
node --test --test-name-pattern="HTTP redirect|secret header" tests/command-guard/security-regressions.test.mjs tests/command-guard/credential-flow.test.mjs
python tests/test-loopback-http-fixture.py
```

Expected: current policy allows unauthenticated redirects and does not classify
the four vendor headers as credentials.

- [x] **Step 4: Add explicit catalogue rejection results**

Add a small helper next to `result`:

```javascript
function rejected(denyReasonCode) {
  return { denyReasonCode };
}
```

Extend the curl flag grammar with `--location-trusted`. In `classifyHttp`,
return `rejected('DENY_UNBOUND_HTTP_REDIRECT')` when the parsed flags contain
`-L`, `--location`, or `--location-trusted`; this also catches a compact short
flag such as `-LsS`. Repeated redirect flags must return the same rejection,
not fall through to a generic unknown-command denial. For PowerShell clients,
require the parsed redirect group to equal the exact string `0`; missing,
repeated, nonnumeric, negative, abbreviated, or positive values return the
same rejection.

In `policy.mjs`, consume the rejection before target/risk handling:

```javascript
const match = lookupFamily(stage, { cwd: event.cwd, env, dialect });
if (match?.denyReasonCode) return denied(match.denyReasonCode, stage.index);
if (!match) return denied('DENY_UNKNOWN_COMMAND', stage.index);
```

Register `DENY_UNBOUND_HTTP_REDIRECT` with guidance that tells the caller to use
the final literal URL directly.

- [x] **Step 5: Generalize literal credential-header recognition**

Add one shared predicate in `redaction.mjs`:

```javascript
function credentialHeaderName(name) {
  const normalized = name.trim().toLowerCase();
  return /(?:^|[-_])(?:authorization|auth|token|secret|credential|password|passphrase)(?:$|[-_])/u.test(normalized) ||
    /(?:^|[-_])(?:api|access|private)[-_]key(?:$|[-_])/u.test(normalized);
}
```

Replace the two exact-name authorization header patterns with one generic
literal-header pattern whose `accept` callback invokes the predicate:

```javascript
{
  kind: 'AUTHORIZATION',
  regex: /\b([!#$%&'*+.^_`|~0-9A-Za-z-]+):\s*([^\s"']+)/gu,
  valueGroup: 2,
  accept: (match) => credentialHeaderName(match[1]),
}
```

Use the same predicate from `headerKind`. Preserve Cookie handling and map
recognized secret headers to `AUTHORIZATION`. Do not classify ordinary
content-negotiation or tracing headers as credentials.

- [x] **Step 6: Add RV-89 fixtures and typed mutations**

Register fixtures for long, trusted, compact, and repeated curl redirect
spellings, both PowerShell clients, all four secret-header families, one
ordinary header, and malformed/file-fed forms. Add predicate IDs and exact
mutants:

```javascript
CATALOGUE_HTTP_REDIRECT_REJECT
CATALOGUE_POWERSHELL_REDIRECT_ZERO
CATALOGUE_POWERSHELL_HEADER_BINDING
REDACTION_SECRET_HEADER
POLICY_CATALOGUE_REJECTION
```

Each witness must call the real policy fixture and assert decision, reason,
credential transport, redaction, requested environment, and modifiers.

- [x] **Step 7: Run GREEN and mutation checks**

Run the Step 3 command, then:

```bash
node --test tests/command-guard/executable-fixtures.test.mjs tests/command-guard/mutation-registry.test.mjs
node tests/command-guard/run-mutations.mjs
```

Expected: all focused tests pass and every new mutant is killed from a pristine
baseline.

- [x] **Step 8: Commit the HTTP boundary**

```bash
git add skills/command-driven-operations/scripts/command-guard tests/command-guard tests/loopback-http-fixture.py tests/test-loopback-http-fixture.py
git commit -m "fix: deny unaudited HTTP redirects"
```

---

### Task 2: Replace local Git prefix recognition with closed parsers

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `tests/command-guard/branches.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-witnesses.mjs`

**Interfaces:**
- Consumes: literal Git argv, `LIMITS.fanOut`, and existing Git risk taxonomy.
- Produces: `parseGitAdd(words)`, `parseGitCommit(words)`, and
  `parseGitTag(words)` returning `{ risk, target }` for accepted forms or
  `{ denyReasonCode: 'DENY_UNSUPPORTED_GIT_FORM' }` after recognized local
  subcommands with invalid or unconsumed grammar.

- [x] **Step 1: Write the accepted Git grammar matrix**

Add direct parser-policy tests for:

```javascript
const accepted = [
  ['git add -- src/app.mjs', 'LOW_RISK_CHANGE'],
  ['git add -A', 'LOW_RISK_CHANGE'],
  ['git add --renormalize .', 'LOW_RISK_CHANGE'],
  ['git commit -m change', 'LOW_RISK_CHANGE'],
  ['git commit -a --signoff -m change', 'LOW_RISK_CHANGE'],
  ['git commit --amend -m change', 'DESTRUCTIVE'],
  ['git tag v1.2.3', 'LOW_RISK_CHANGE'],
  ['git tag -a v1.2.3 -m release', 'LOW_RISK_CHANGE'],
  ['git tag -s v1.2.3 -m release', 'LOW_RISK_CHANGE'],
  ['git tag -f v1.2.3', 'DESTRUCTIVE'],
  ['git tag -d v1.2.3', 'DESTRUCTIVE'],
];
```

Assert accepted low-risk forms ask normally and allow in bypass; destructive
forms ask in both modes. Assert canonical target values rather than the last
raw argument.

- [x] **Step 2: Write the rejected Git grammar matrix**

Cover unknown and unconsumed options, duplicate singleton options, conflicting
scope/sign modes, dynamic paths, excessive operands/messages, missing message
or tag name, interactive `-p/-i/-e`, message/path files, editor-dependent
commit, `--fixup`, `--squash`, `-c`, `-C`, and configuration overrides. Every
case must deny in default and bypass modes.
Assert `DENY_UNSUPPORTED_GIT_FORM` for every rejected `add`, `commit`, or `tag`
form so the operator receives Git-specific reformulation guidance.

- [x] **Step 3: Run the Git RED suite**

```bash
node --test --test-name-pattern="local Git closed grammar|Git workflow" tests/command-guard/security-regressions.test.mjs tests/command-guard/branches.test.mjs
```

Expected: prefix-recognized destructive and unsupported forms are still
accepted, and several supported target bindings are not canonical.

- [x] **Step 4: Implement bounded literal helpers and three parsers**

Rely on the Bash lexer for the global token-length bound, then use literal
operand and Git-object helpers for dynamic-character and revision-grammar
rejection. Enforce fan-out in each parser. Implement each parser as a single pass over
argv with explicit value options, flags, singleton groups, `--` handling, and
complete consumption. Once exact dispatch recognizes `add`, `commit`, or
`tag`, convert parser failure to
`rejected('DENY_UNSUPPORTED_GIT_FORM')`; leave unrelated unknown Git
subcommands on the generic unknown-command path. Register the reason code and
guidance to use only finite literal options and operands. Return examples:

```javascript
{ risk: 'LOW_RISK_CHANGE', target: 'paths:src/app.mjs' }
{ risk: 'DESTRUCTIVE', target: 'commit:HEAD' }
{ risk: 'DESTRUCTIVE', target: 'tag:v1.2.3' }
```

Replace the `add|commit|tag` regex and the overlapping tag delete prefix with
exact parser dispatch. Do not inspect or neutralize hooks, filters, or signers.

- [x] **Step 5: Add RV-90 fixtures and typed mutations**

Add source/installed fixtures for basic success, `commit --amend`, `tag -f`,
tag deletion, signed tag, add renormalization, interactive/file-fed denial, and
unknown option denial. Add and witness:

```javascript
CATALOGUE_GIT_LOCAL_CLOSED_GRAMMAR
CATALOGUE_GIT_COMMIT_AMEND_RISK
CATALOGUE_GIT_TAG_FORCE_RISK
CATALOGUE_GIT_TAG_DELETE_RISK
POLICY_GIT_UNSUPPORTED_FORM_GUIDANCE
```

- [x] **Step 6: Run GREEN and mutation checks**

Run the Step 3 command plus executable fixtures and the full mutation runner.
Expected: every matrix case and mutant passes without weakening RV-76 through
RV-88.

- [x] **Step 7: Commit the Git parsers**

```bash
git add skills/command-driven-operations/scripts/command-guard tests/command-guard
git commit -m "fix: close local Git write grammars"
```

---

### Task 3: Make Kubernetes prune destructive

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-witnesses.mjs`

**Interfaces:**
- Consumes: the existing closed kubectl option grammar and `enabledBooleanOption`.
- Produces: enabled `apply --prune` risk `DESTRUCTIVE` for kubectl and k3s.

- [x] **Step 1: Add failing prune risk tests**

```javascript
for (const prefix of ['kubectl', 'k3s kubectl']) {
  const command = `${prefix} --context prod apply --prune -l app=demo -f manifest.yaml`;
  for (const mode of ['default', 'bypassPermissions']) {
    const result = analyze(command, mode);
    assert.equal(result.decision, 'ask', `${mode}: ${command}`);
    assert.equal(result.risk, 'DESTRUCTIVE', command);
  }
}
```

Also retain a non-pruning apply control as `DISRUPTIVE_CHANGE` and test repeated,
malformed, and false-valued prune spellings according to the existing grammar.

- [x] **Step 2: Run RED**

```bash
node --test --test-name-pattern="apply prune" tests/command-guard/security-regressions.test.mjs
```

Expected: bypass returns allow and risk remains `DISRUPTIVE_CHANGE`.

- [x] **Step 3: Implement minimal risk derivation**

Before the existing risk expression, derive the value through the existing
closed boolean-option helper so both separated and inline forms agree:

```javascript
const destructivePrune = verb === 'apply' && enabledBooleanOption(words, '--prune');
```

Include it with delete, drain, and force-replace in the `DESTRUCTIVE` branch.

- [x] **Step 4: Add RV-91 fixtures and one mutation**

Register kubectl and k3s cases plus the non-prune control. Add
`CATALOGUE_KUBECTL_PRUNE_RISK`, mutate `destructivePrune` to false, and witness
both client paths.

- [x] **Step 5: Run GREEN and commit**

Run the focused test, executable fixtures, and mutation runner, then:

```bash
git add skills/command-driven-operations/scripts/command-guard tests/command-guard
git commit -m "fix: classify Kubernetes prune as destructive"
```

---

### Task 4: Require profile-free PowerShell wrappers

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `tests/command-guard/lexer.test.mjs`
- Modify: `tests/command-guard/policy.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-witnesses.mjs`
- Modify: `tests/live-command-guard-smoke.sh`

**Interfaces:**
- Consumes: the outer Bash token stream and `lexPowerShell(payload)`.
- Produces: exact wrapper grammar and `DENY_POWERSHELL_PROFILE` guidance.

- [x] **Step 1: Add failing wrapper tests**

Cover `pwsh` and `powershell` with these classes:

```javascript
const denied = [
  'pwsh -Command "Get-Service"',
  'powershell -Command "Get-Service"',
  'pwsh -NoProfile -NoProfile -Command "Get-Service"',
  'pwsh -NoLog -Command "Get-Service"',
  'pwsh -Sta -Mta -NoProfile -Command "Get-Service"',
];
const allowed = [
  'pwsh -NoProfile -Command "Get-Service"',
  'powershell -NoProfile -NonInteractive -NoLogo -Command "Get-Service"',
];
```

Missing or duplicate `-NoProfile` must deny with
`DENY_POWERSHELL_PROFILE`; other grammar failures use
`DENY_UNSUPPORTED_SYNTAX`. Preserve outer-composition and exact payload-arity
tests.

- [x] **Step 2: Run RED**

```bash
node --test --test-name-pattern="PowerShell wrapper|profile-free" tests/command-guard/policy.test.mjs tests/command-guard/security-regressions.test.mjs
```

Expected: missing profile suppression and accepted abbreviation expose the old
behavior.

- [x] **Step 3: Implement typed wrapper rejection**

Add an internal helper that throws a reason-bearing error only for the missing
or duplicate profile condition. In the top-level catch, allow only the known
internal reason; every other exception remains `DENY_UNSUPPORTED_SYNTAX`.

Validate canonical case-insensitive option names, uniqueness, `Sta`/`Mta`
exclusion, exactly one `-Command`, and exactly one payload. Replace `-nolog`
with canonical `-nologo`.

- [x] **Step 4: Add RV-92 fixtures and one mutation**

Register both missing-profile wrappers, canonical allowed wrappers, duplicate,
abbreviation, conflict, and arity cases. Add
`POLICY_POWERSHELL_NOPROFILE_REQUIRED`; its witness must assert the dedicated
reason and that a canonical wrapper still allows.

- [x] **Step 5: Update live self-test, run GREEN, and commit**

Ensure every live PowerShell wrapper includes `-NoProfile` (the existing smoke
wrapper was already compliant, so no script edit was required). Run focused tests,
the live smoke self-test, executable fixtures, and mutations, then:

```bash
git add skills/command-driven-operations/scripts/command-guard tests/command-guard tests/live-command-guard-smoke.sh
git commit -m "fix: require profile-free PowerShell wrappers"
```

---

### Task 5: Add JavaScript CodeQL coverage

**Files:**
- Create: `tests/test-ci-workflows.py`
- Modify: `.github/workflows/security.yml`
- Modify: `tests/validate-package.sh`
- Modify: `tests/validate-ci-workflows.sh`

**Interfaces:**
- Consumes: repository workflow YAML and existing pinned CodeQL actions.
- Produces: executable assertion that the CodeQL matrix contains exactly the
  required Python and JavaScript/TypeScript languages.

- [x] **Step 1: Write a failing workflow mutation test**

Create a unittest that copies `.github/workflows/security.yml` and
`tests/validate-ci-workflows.sh` into a temporary repository and executes the
validator. In separate subtests, rewrite
`language: [python, javascript-typescript]` to each of
`language: [python]` and `language: [javascript-typescript]`; assert a nonzero
exit containing `security.yml CodeQL languages`. The pristine copy must pass.

- [x] **Step 2: Run RED**

```bash
python tests/test-ci-workflows.py
```

Expected: the pristine workflow fails because JavaScript/TypeScript is absent.

- [x] **Step 3: Extend the validator and workflow**

Add a security-workflow-specific check in `validate-ci-workflows.sh` that
requires the exact two-member language set, rejecting either omission and
unexpected extras. Change the matrix to:

```yaml
matrix:
  language: [python, javascript-typescript]
```

Add `python3 tests/test-ci-workflows.py` to `validate-package.sh`.

- [x] **Step 4: Run GREEN and workflow validation**

```bash
python tests/test-ci-workflows.py
bash tests/validate-ci-workflows.sh
```

Expected: pristine validation passes and removal of either language fails.

- [x] **Step 5: Commit**

```bash
git add .github/workflows/security.yml tests/test-ci-workflows.py tests/validate-ci-workflows.sh tests/validate-package.sh
git commit -m "ci: analyze command guard JavaScript"
```

---

### Task 6: Align architecture, operator guidance, and review evidence

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `docs/superpowers/specs/2026-08-03-p0-04-post-rv88-remediation-design.md`
- Modify: `.cspell.json` only if new technical terms require it

**Interfaces:**
- Consumes: final implemented predicates, fixture count, mutation count, test
  count, and approved scope boundary.
- Produces: one consistent operator and architecture description for PR #25.

- [x] **Step 1: Append the next independent-review disposition**

Record the fresh review findings as stable IDs:

```text
RV-89 unaudited HTTP redirects and unrecognized secret headers
RV-90 prefix-based local Git direct semantics
RV-91 destructive Kubernetes prune
RV-92 PowerShell profile loading
RV-93 missing JavaScript CodeQL coverage
```

Mark runtime findings remediated with final verification pending. Record the
Git indirect-process exclusion as an approved residual risk, not as a fixed
finding.

- [x] **Step 2: Correct architecture claims**

Update README and ADR-004 to state that requested HTTP origin is not an
effective redirect target, redirects deny, PowerShell wrappers require
`-NoProfile`, direct Git semantics are closed, and Git hooks/filters/signers are
outside scope. Remove or qualify claims contradicted by the review.

- [x] **Step 3: Update release notes without changing version**

Add concise 0.11.0 changelog bullets for RV-89 through RV-93. Derive executable
test, fixture, and mutation counts from the test runner and registries, and
update the documents only from that fresh output. Keep all runtime and model
versions unpinned.

- [ ] **Step 4: Mark the approved spec implemented**

Change the approved spec status to `Implemented and independently verified`
only after source and installed tests and the fresh independent review pass.
Record exact behavior rather than implementation history.

- [x] **Step 5: Validate and commit documentation**

```bash
npx --yes markdownlint-cli2 "**/*.md" "#.tmp/**"
npx --yes cspell "README.md" "CHANGELOG.md" "docs/architecture/ADR-004-native-command-guard.md" "docs/reviews/2026-07-26-pr-25-independent-review.md" "docs/superpowers/specs/2026-08-03-p0-04-post-rv88-remediation-design.md"
python tests/validate-content.py
python tests/test-architecture-docs.py
git diff --check
```

Then commit:

```bash
git add README.md CHANGELOG.md docs/architecture/ADR-004-native-command-guard.md docs/reviews/2026-07-26-pr-25-independent-review.md docs/superpowers/specs/2026-08-03-p0-04-post-rv88-remediation-design.md .cspell.json
git commit -m "docs: record post-RV-88 remediation"
```

---

### Task 7: Run complete verification and independent review

**Files:**
- Modify only when a gate exposes a defect.
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md` after a clean
  independent verdict.

**Interfaces:**
- Consumes: final source and documentation commits.
- Produces: clean local/package evidence and an independent merge verdict.

- [x] **Step 1: Run the complete source gate**

```bash
node tests/run-command-guard-tests.mjs
```

Require zero failures/skips, 100 percent critical line/function/branch
coverage, all pristine witnesses passing, and every typed mutant killed.

- [x] **Step 2: Run repository validators**

```bash
python tests/test-command-guard-install-policy.py
python tests/validate-content.py
python tests/test-risk-taxonomy.py
python tests/test-subagent-frontmatter.py
python tests/test-installed-subagents.py
python tests/test-schema-validation.py
python tests/test-architecture-docs.py
python tests/test-ci-workflows.py
bash tests/validate-ci-workflows.sh
git diff --check
```

- [x] **Step 3: Run the installed Debian/WSL package gate**

```bash
command -v node
node --version
bash tests/validate-package.sh
```

If the configured WSL Node lacks the required native coverage facilities, load
the existing NVM installation and select its current LTS release with
`nvm install --lts && nvm use --lts`, then rerun the three commands. Record the
observed version as test evidence only; do not add it as a package requirement
or version pin. Require source-to-installed byte equivalence and execution of
all review fixtures.

- [x] **Step 4: Request a fresh independent adversarial review**

Review the final head against the pre-remediation commit `24a3331`. Require
explicit checks for RV-89 through RV-93, adjacent HTTP/Git/Kubernetes/
PowerShell bypasses, mutation quality, installed behavior, documentation, and
workflow coverage. Do not reuse the earlier verdict.

- [ ] **Step 5: Remediate every confirmed finding**

For each finding, reproduce RED, implement the smallest correction, rerun the
affected and full gates, and request another independent review. Do not mark
the ledger resolved while any Critical or Important finding remains.

The review of `02e480b` produced RV-94 through RV-97. Their implementation
requires the first-argument curl default-configuration disable boundary,
platform key-header credential recognition, exact fail-closed CodeQL job,
matrix, `init`, `analyze`, and `with.languages` wiring validation,
platform-qualified test evidence, 155 source/installed fixtures,
and 82 typed mutation witnesses. Focused Windows gates are green; Debian/WSL,
the complete repository gate, and the next independent verdict remain pending.

- [ ] **Step 6: Record the final independent verdict**

Append exact gate counts and the final severity summary to the ledger, lint the
changed document, and commit:

```bash
git add docs/reviews/2026-07-26-pr-25-independent-review.md
git commit -m "docs: record final post-RV-88 review"
```

---

### Task 8: Update PR #25 and verify GitHub state

**Files:**
- No additional repository file is expected.
- External write: existing PR #25 branch, body, and evidence comment.

**Interfaces:**
- Consumes: clean final commit, independent verdict, and local gate evidence.
- Produces: updated PR head/body with green required checks.

- [ ] **Step 1: Push the existing branch**

```bash
git push origin agent/p0-04-command-guard
```

Verify local HEAD equals the remote branch head. Do not create another PR.

- [ ] **Step 2: Replace stale PR evidence**

Update the body to the final head and actual counts. Describe the approved Git
residual-risk boundary and remove obsolete Ready/test/mutation/fixture values.
Add a concise comment linking the versioned ledger and final independent
verdict. Do not include credentials, local machine details, or unverified
claims.

- [ ] **Step 3: Watch all checks to terminal state**

```bash
gh pr checks 25 --repo marcoaureliocardoso/senior-infra-ops-analyst --watch --interval 10
```

Inspect every failure log. Retry only a proven transient external failure; fix
deterministic failures through a new RED/GREEN cycle.

- [ ] **Step 4: Confirm completion state**

Require PR `OPEN`, `MERGEABLE`, `CLEAN`, final head equality, all required
checks successful, no unresolved review threads, and a clean worktree. Report
that the PR is ready, but do not merge without a separate request.
