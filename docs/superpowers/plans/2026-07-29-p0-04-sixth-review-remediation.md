# P0-04 Sixth Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four findings from the sixth independent review by validating Redis verb semantics, requiring confirmation for mutable HTTP effects, and extending the critical coverage and mutation gates to the command catalogue.

**Architecture:** Keep the existing closed executable-option parsers and add a closed Redis verb parser that consumes every positional argument before producing a policy result. Preserve the canonical Redis environment as the sole binding domain, attach `EXTERNAL_SIDE_EFFECT` to uncatalogued mutable HTTP requests, and make the existing native Node gate measure and mutate the catalogue directly.

**Tech Stack:** ECMAScript modules, Node.js native test runner and coverage, deterministic source-rewrite mutation harness, Python repository validators, Bash/PowerShell syntax gates, Nori installed-artifact validation.

**Execution note:** The intermediate commit steps are review checkpoints, not
separate publication requirements. They were evaluated and deliberately
deferred because this shared worktree already contained overlapping uncommitted
PR remediations. Publication remains a separate action after independent
review, so no partial commit obscures ownership of the combined delta.

## Global Constraints

- Do not pin Claude Code, Nori, DeepSeek, or Node.js versions; probe required runtime capabilities.
- Do not persist or print credentials, command text, credential hashes, or model-visible secret values.
- `DESTRUCTIVE` and `EXTERNAL_SIDE_EFFECT` operations must return `ask` in every permission mode.
- Unknown, incomplete, dynamic, repeated, or unconsumed syntax must fail closed.
- Preserve RV-31 through RV-36 and source-to-installed semantic equivalence.
- Use only synthetic credential markers and `.invalid` destinations in tests.

---

### Task 1: Close the Redis verb grammar

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: `parseRedisInvocation(argv) -> { commandIndex, values, flags } | null` and `canonicalRedisEnvironment(invocation) -> string | null`.
- Produces: `parseRedisCommand(words, commandIndex) -> { risk, target } | null`, consumed only by the Redis branch of `lookupFamily()`.

- [x] **Step 1: Add failing Redis behavior tests**

Add table-driven policy assertions with hand-derived expected decisions and risks:

```js
test('Redis EXPIRE validates deletion semantics and complete literal grammar', () => {
  const cases = [
    ['redis-cli EXPIRE cache:key 60', 'allow', 'LOW_RISK_CHANGE'],
    ['redis-cli EXPIRE cache:key 60 NX', 'allow', 'LOW_RISK_CHANGE'],
    ['redis-cli EXPIRE cache:key 0', 'ask', 'DESTRUCTIVE'],
    ['redis-cli EXPIRE cache:key -1', 'ask', 'DESTRUCTIVE'],
    ['redis-cli EXPIRE cache:key $TTL', 'deny', null],
    ['redis-cli EXPIRE cache:key', 'deny', null],
    ['redis-cli EXPIRE cache:key 60 NX XX', 'deny', null],
  ];
  for (const [command, decision, risk] of cases) {
    const result = analyze(command);
    assert.equal(result.decision, decision, command);
    if (risk) assert.equal(result.risk, risk, command);
  }
});

test('Redis composite client termination accepts only bounded literal targets', () => {
  for (const command of [
    'redis-cli CLIENT KILL 192.0.2.10:6379',
    'redis-cli CLIENT KILL ID 42',
  ]) {
    const normal = analyze(command, 'default');
    const permissive = analyze(command, 'bypassPermissions');
    assert.equal(normal.decision, 'ask', command);
    assert.equal(permissive.decision, 'allow', command);
    assert.equal(permissive.risk, 'DISRUPTIVE_CHANGE', command);
  }
  for (const command of [
    'redis-cli KILL 192.0.2.10:6379',
    'redis-cli CLIENT KILL ID $CLIENT_ID',
    'redis-cli CLIENT KILL TYPE normal',
    'redis-cli CLIENT KILL',
  ]) assert.equal(analyze(command).decision, 'deny', command);
});
```

Also cover `PERSIST` with one literal key, missing/extra operands, dynamic keys,
positive `EXPIRE` with `XX`, `GT`, and `LT`, non-integer TTLs, and extra tokens.
Add stable RV-37 and RV-38 source/installed fixtures for the destructive TTL and
composite command corrections.

- [x] **Step 2: Run the focused tests and witness RED**

Run:

```powershell
node --test --test-name-pattern="Redis EXPIRE|Redis composite|review regression" tests/command-guard/security-regressions.test.mjs tests/command-guard/executable-fixtures.test.mjs
```

Expected: failures show non-positive `EXPIRE` receiving `allow`, malformed
forms being classified, and both supported `CLIENT KILL` forms receiving
`deny`. Existing Redis binding cases must remain green.

- [x] **Step 3: Implement the minimal closed Redis command parser**

Add literal helpers and a verb parser near the Redis connection helpers:

```js
function literalRedisOperand(value) {
  return typeof value === 'string' && value.length > 0 && !/[$*?{}]/u.test(value);
}

function parseRedisCommand(words, commandIndex) {
  const verb = words[commandIndex]?.toUpperCase();
  const args = words.slice(commandIndex + 1);
  if (verb === 'EXPIRE') {
    if (args.length < 2 || args.length > 3 || !literalRedisOperand(args[0]) || !/^-?\d+$/u.test(args[1])) return null;
    if (args[2] && !['NX', 'XX', 'GT', 'LT'].includes(args[2].toUpperCase())) return null;
    return { risk: Number(args[1]) <= 0 ? 'DESTRUCTIVE' : 'LOW_RISK_CHANGE', target: args[0] };
  }
  if (verb === 'PERSIST') return args.length === 1 && literalRedisOperand(args[0]) ? { risk: 'LOW_RISK_CHANGE', target: args[0] } : null;
  if (verb === 'CLIENT') {
    if (args[0]?.toUpperCase() !== 'KILL') return null;
    if (args.length === 2 && literalRedisOperand(args[1]) && /^[^:\s]+:\d{1,5}$/u.test(args[1])) return { risk: 'DISRUPTIVE_CHANGE', target: args[1] };
    if (args.length === 3 && args[1]?.toUpperCase() === 'ID' && boundedInteger(args[2], Number.MAX_SAFE_INTEGER)) return { risk: 'DISRUPTIVE_CHANGE', target: `id:${args[2]}` };
    return null;
  }
  // Preserve the existing exact grammars for reads and other changes, but
  // require the parser to consume all operands before returning a result.
}
```

Implement the remaining accepted verbs with these exact finite grammars:

- `PING` has no operands; `INFO` has zero or one literal section;
- `GET` has one literal key and `MGET` has between one and
  `LIMITS.outputRows` literal keys;
- `SCAN` is exactly `SCAN <non-negative-cursor> COUNT <bounded-positive-count>`;
- `REPLICAOF` is either `REPLICAOF NO ONE` or a literal host plus bounded port;
- `DEL` has between one and `LIMITS.fanOut` literal keys;
- `FLUSHALL`, `FLUSHDB`, and `SHUTDOWN` have no operands; and
- `CONFIG` is exactly `CONFIG SET <literal-parameter> <literal-value>`.

Return `SAFE_READ_ONLY`, `DISRUPTIVE_CHANGE`, or `DESTRUCTIVE` exactly as the
existing policy table specifies. Replace the Redis branch's regex/risk ternary
with the parser result, and derive `target` only from the parser result.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2 and then:

```powershell
node --test tests/command-guard/security-regressions.test.mjs tests/command-guard/policy.test.mjs tests/command-guard/executable-fixtures.test.mjs
```

Expected: all selected tests pass; RV-31 through RV-36 fixtures remain green.

- [x] **Step 5: Evaluate the Redis grammar commit checkpoint**

```powershell
git add -- skills/command-driven-operations/scripts/command-guard/catalogue.mjs tests/command-guard/security-regressions.test.mjs tests/command-guard/review-regression-fixtures.mjs
git commit -m "fix: close Redis verb semantics"
```

### Task 2: Require confirmation for mutable HTTP effects

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/policy.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: the existing HTTP method, origin, path, body/upload, and sink derivation.
- Produces: mutable HTTP results with `risk: 'DISRUPTIVE_CHANGE'` and `modifiers: ['EXTERNAL_SIDE_EFFECT']`, plus existing modifiers such as `FILE_WRITE` where applicable.

- [x] **Step 1: Add failing HTTP policy tests**

```js
test('uncatalogued mutable HTTP effects always require operator confirmation', () => {
  for (const mode of ['default', 'bypassPermissions']) {
    for (const command of [
      'curl -X POST https://api.example.invalid/restart',
      'curl -X PUT https://api.example.invalid/items/1',
      'curl -X PATCH https://api.example.invalid/approvals/1',
      'Invoke-RestMethod -Uri https://api.example.invalid/messages -Method POST -Body value',
    ]) {
      const result = analyze(command, mode);
      assert.equal(result.decision, 'ask', `${mode}: ${command}`);
      assert.equal(result.risk, 'DISRUPTIVE_CHANGE', command);
      assert.ok(result.modifiers.includes('EXTERNAL_SIDE_EFFECT'), command);
    }
  }
});
```

Add controls proving `GET`/`HEAD` retain their existing decisions and `DELETE`
remains `DESTRUCTIVE`. Add a stable RV-39 installed fixture.

- [x] **Step 2: Run the focused test and witness RED**

Run:

```powershell
node --test --test-name-pattern="mutable HTTP|review regression" tests/command-guard/security-regressions.test.mjs tests/command-guard/executable-fixtures.test.mjs
```

Expected: bypass-mode `POST`, `PUT`, and `PATCH` return `allow` or lack the
external-effect modifier.

- [x] **Step 3: Implement the minimal HTTP classification change**

Replace the method-only low-risk branch with explicit risk and modifiers:

```js
const mutable = ['PUT', 'PATCH', 'POST'].includes(method);
const risk = ['GET', 'HEAD'].includes(method)
  ? 'SAFE_READ_ONLY'
  : method === 'DELETE'
    ? 'DESTRUCTIVE'
    : mutable
      ? 'DISRUPTIVE_CHANGE'
      : null;
const modifiers = [
  ...(hasSink ? ['FILE_WRITE'] : []),
  ...(mutable ? ['EXTERNAL_SIDE_EFFECT'] : []),
];
```

Retain the existing sink escalation for otherwise read-only requests. Do not
introduce an origin allowlist in this task.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2 and the complete HTTP security-regression section.
Expected: all mutable methods ask in both modes; read and delete controls pass.

- [x] **Step 5: Evaluate the HTTP correction commit checkpoint**

```powershell
git add -- skills/command-driven-operations/scripts/command-guard/catalogue.mjs tests/command-guard/security-regressions.test.mjs tests/command-guard/policy.test.mjs tests/command-guard/review-regression-fixtures.mjs
git commit -m "fix: require approval for mutable HTTP effects"
```

### Task 3: Put the catalogue behind critical coverage and mutations

**Files:**
- Modify: `tests/run-command-guard-tests.mjs`
- Modify: `tests/command-guard/coverage-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-invariant.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`

**Interfaces:**
- Consumes: Node native `--test-coverage-include` thresholds and `MUTATIONS` source-rewrite records.
- Produces: a 100 percent critical coverage gate including `catalogue.mjs`, with dedicated mutation witnesses selected by `COMMAND_GUARD_MUTATION_ID`.

- [x] **Step 1: Add catalogue to the critical coverage set and witness failure**

Add `'catalogue.mjs'` to the `critical` filename array in
`tests/run-command-guard-tests.mjs`, then run:

```powershell
node tests/run-command-guard-tests.mjs
```

Expected: the coverage gate fails and prints the uncovered catalogue lines,
branches, or functions. Record those gaps before changing fixtures.

- [x] **Step 2: Add behavior-bearing fixtures for uncovered catalogue paths**

Extend `coverage-fixtures.mjs` or direct tests only where the path represents a
real supported or rejected behavior. Use literal expected policy IDs, risks,
targets, environments, modifiers, or deny decisions. Do not add source-text
assertions or fixtures whose only assertion is that execution did not throw.

Run:

```powershell
node --test tests/command-guard/coverage.test.mjs tests/command-guard/security-regressions.test.mjs
```

Expected: selected tests pass and every added fixture has an observable policy
expectation.

- [x] **Step 3: Register catalogue mutations and witness surviving mutants**

Add deterministic source replacements whose exact `search` strings occur once
after Tasks 1 and 2. Required mutation IDs:

```js
'CATALOGUE_REDIS_EXPIRE_DELETE'
'CATALOGUE_REDIS_LITERAL_OPERAND'
'CATALOGUE_REDIS_CLIENT_KILL'
'CATALOGUE_REDIS_CANONICAL_ENVIRONMENT'
'CATALOGUE_REDIS_UNKNOWN_OPTION'
'CATALOGUE_HTTP_EXTERNAL_EFFECT'
```

Add corresponding `switch` cases in `mutation-invariant.test.mjs` that assert
real policy behavior with literal expected results. Before adding each witness,
run `node tests/command-guard/run-mutations.mjs` and confirm the new mutant
survives or the registry/witness mismatch fails for the expected reason.

- [x] **Step 4: Add the dedicated mutation witnesses and verify GREEN**

Each switch case must isolate one invariant, for example:

```js
case 'CATALOGUE_REDIS_EXPIRE_DELETE': {
  const result = await policyFixture('redis-cli EXPIRE cache:key 0');
  assert.equal(result.decision, 'ask');
  assert.equal(result.risk, 'DESTRUCTIVE');
  break;
}
case 'CATALOGUE_HTTP_EXTERNAL_EFFECT': {
  const result = await policyFixture('curl -X POST https://api.example.invalid/restart');
  assert.equal(result.decision, 'ask');
  assert.ok(result.modifiers.includes('EXTERNAL_SIDE_EFFECT'));
  break;
}
```

Run:

```powershell
node tests/command-guard/run-mutations.mjs
node tests/run-command-guard-tests.mjs
```

Expected: every registered mutation is killed and the catalogue-inclusive
critical coverage gate reaches 100 percent line/function/branch coverage.

- [x] **Step 5: Evaluate the gate correction commit checkpoint**

```powershell
git add -- tests/run-command-guard-tests.mjs tests/command-guard/coverage-fixtures.mjs tests/command-guard/mutations.mjs tests/command-guard/mutation-invariant.test.mjs tests/command-guard/security-regressions.test.mjs
git commit -m "test: cover and mutate command catalogue"
```

### Task 4: Record the seventh disposition and operator semantics

**Files:**
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`

**Interfaces:**
- Consumes: observed RED/GREEN and full-gate counts from Tasks 1 through 3.
- Produces: versioned architecture and review records that distinguish local remediation from independent confirmation.

- [x] **Step 1: Update architecture and operator documentation**

Document the closed Redis verb grammar, non-positive TTL escalation, supported
`CLIENT KILL` forms, mutable HTTP confirmation rule, catalogue-inclusive
coverage, and mutation witnesses. Preserve the existing statement that
permission mode changes approval policy but never disables validation.

- [x] **Step 2: Add RV-37 through RV-40 to the review disposition**

Record exactly:

- RV-37: non-positive/dynamic `EXPIRE` semantics;
- RV-38: `CLIENT KILL` composite grammar;
- RV-39: mutable HTTP effects without exact route policy; and
- RV-40: catalogue coverage and mutation-gate omission.

Mark each as locally remediated with independent verification pending. Insert
fresh test counts only after Task 5 produces them.

- [x] **Step 3: Update README and changelog only where operator behavior changed**

State that mutable HTTP methods remain available but always request approval,
and that Redis TTL/client termination is classified from complete literal
grammar. Add the four review closures to the existing unreleased `0.11.0`
entry; do not introduce a new version solely for review remediation.

- [x] **Step 4: Run documentation validation**

```powershell
python tests/validate-content.py
python tests/test-architecture-docs.py
git diff --check
```

Expected: all validators exit zero and no whitespace errors are reported.

- [x] **Step 5: Evaluate the documentation commit checkpoint**

```powershell
git add -- docs/reviews/2026-07-26-pr-25-independent-review.md docs/architecture/ADR-004-native-command-guard.md README.md CHANGELOG.md tests/command-guard/review-regression-fixtures.mjs docs/superpowers/plans/2026-07-29-p0-04-sixth-review-remediation.md
git commit -m "docs: record sixth review remediation"
```

### Task 5: Execute the complete verification matrix

**Files:**
- Modify only if a test exposes a requirement defect; return to the owning task's RED–GREEN cycle first.

**Interfaces:**
- Consumes: the complete source tree and Nori packaging metadata.
- Produces: fresh evidence suitable for the review disposition and merge decision.

- [x] **Step 1: Run the complete native Node gate**

```powershell
node tests/run-command-guard-tests.mjs
```

Expected: all unit, property, finite-matrix, 100 percent critical coverage, and
mutation gates pass on a capability-compatible Node runtime.

- [x] **Step 2: Run the repository package and host syntax gates**

From Debian WSL, translate the worktree with `wslpath` and run:

```bash
cd "$(wslpath 'C:\projects\senior-infra-ops-analyst\senior-infra-ops-analyst\.worktrees\p0-04-command-guard')"
bash tests/validate-package.sh
```

From PowerShell, run:

```powershell
pwsh -NoProfile -File tests/validate-powershell-syntax.ps1
python tests/test-command-guard-install-policy.py
python tests/validate-content.py
python tests/test-risk-taxonomy.py
python tests/test-subagent-frontmatter.py
python tests/test-installed-subagents.py
python tests/test-schema-validation.py
python tests/test-architecture-docs.py
python tests/test-live-smoke-safety.py
python tests/test-load-claude-env.py
python tests/test-loopback-http-fixture.py
python tests/test-live-command-guard-safety.py
python tests/test-smoke-command-guard.py
```

Expected: every command exits zero; no Claude process is started and no
provider credential is loaded.

- [x] **Step 3: Validate an isolated Nori-installed artifact**

In Debian WSL, create a directory with `mktemp -d`, set its `HOME` and
`CLAUDE_CONFIG_DIR`, resolve `sks` or `nori-skillsets`, and execute the same
`link <worktree> --name senior-infra-ops-analyst` plus `switch
senior-infra-ops-analyst --agent claude-code` sequence implemented by
`install_with_nori()` in `tests/live-command-guard-smoke.sh`. Then run:

```bash
python3 tests/validate-installed-subagents.py \
  --installed-agents-dir "$CLAUDE_CONFIG_DIR/agents" \
  --installed-skills-dir "$CLAUDE_CONFIG_DIR/skills"
node tests/command-guard/run-installed-corpus.mjs \
  "$CLAUDE_CONFIG_DIR/skills/command-driven-operations/scripts"
```

Compare every source file under `skills/command-driven-operations/scripts`
with the corresponding installed file using `cmp -s`. Expected: 12 subagents,
24 skills, byte equivalence, and every RV fixture passes. Resolve the temporary
path with `readlink -f`, verify it remains under `${TMPDIR:-/tmp}`, and remove
only that exact path afterward.

- [x] **Step 4: Run final hygiene checks**

```powershell
git diff --check origin/main
git status --short --untracked-files=all
```

Also scan the changed tree for credential markers, retained runtime artifacts,
unchecked plan boxes, and pins of Claude Code, Nori, DeepSeek, or Node.js.
Expected: no retained secrets/artifacts, no unintended pins, and only expected
project changes.

- [x] **Step 5: Record exact evidence and evaluate the evidence commit checkpoint**

Replace provisional counts in the review record with fresh observed counts,
rerun documentation validation, and commit only those evidence updates:

```powershell
git add -- docs/reviews/2026-07-26-pr-25-independent-review.md docs/superpowers/plans/2026-07-29-p0-04-sixth-review-remediation.md
git commit -m "docs: record sixth remediation verification"
```

Do not claim readiness to merge until a subsequent independent read-only review
confirms RV-37 through RV-40 on the resulting tree.
