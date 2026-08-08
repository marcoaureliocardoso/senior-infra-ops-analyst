# P0-04 Eighth Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five remaining PR #25 review findings with complete client grammars, canonical local-file effects, bounded database credential domains, destructive Git alias parity, and a mutation protocol that proves each witness against pristine and mutated source.

**Architecture:** Preserve the catalogue's public `lookupFamily()` result
contract while adding one focused output-path resolver and closed
client-specific parsers. Pass only validated hook `cwd` and an explicitly
queried environment into policy analysis. Replace mutation witness labels and
the switch with an executable map plus a child-process protocol that
distinguishes semantic assertion failures from infrastructure failures.

**Tech Stack:** ECMAScript modules, Node.js native test runner and coverage, deterministic source-rewrite mutation testing, Python repository validators, Bash/PowerShell syntax validation, Debian/WSL, and isolated Nori installed-artifact validation.

## Global Constraints

- Implement the approved design in `docs/superpowers/specs/2026-07-29-p0-04-eighth-review-remediation-design.md` exactly.
- Do not pin Claude Code, Nori, DeepSeek, Node.js, or any model/runtime version; use capability probes and record observed versions only as evidence.
- Do not start Claude or load model-provider credentials in deterministic validation.
- Never persist or print raw commands, credential values, request bodies, complete environments, or secret-derived identifiers.
- Every accepted local file sink has `FILE_WRITE` plus `ALWAYS_ASK`, including in `bypassPermissions`.
- Unknown, incomplete, dynamic, repeated-singleton, or unconsumed syntax fails closed.
- Preserve all existing RV-01 through RV-40 behavior unless this plan explicitly strengthens it.
- Use synthetic credential markers and `.invalid` destinations in tests.
- This is a shared dirty worktree. Before each commit checkpoint, inspect the exact staged file list. Commit only changes whose ownership is unambiguous; otherwise record the checkpoint as deferred and leave the combined PR delta intact.

---

### Task 1: Carry hook context and resolve canonical output paths

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/output-path.mjs`
- Create: `tests/command-guard/output-path.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/contract.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/validate-ops-command.mjs`
- Modify: `tests/command-guard/contract.test.mjs`
- Modify: `tests/command-guard/helpers.mjs`
- Modify: `tests/run-command-guard-tests.mjs`

**Interfaces:**
- `parseHookEvent(raw)` adds `cwd: string | null` to its frozen normalized result.
- `analyzeCommand(event, env = {})` passes `{ cwd, env, dialect }` into `lookupFamily(stage, context)`.
- `lookupFamily(stage, context = {})` accepts a context without changing its returned policy-result shape.
- `resolveOutputPath(operand, { cwd = null, env = {}, dialect = 'bash' } = {}) -> string | null` returns one canonical POSIX or Windows path or `null`.

- [x] **Step 1: Add failing contract and resolver tests**

Add to `contract.test.mjs`:

```js
test('hook contract preserves bounded cwd for effect binding', () => {
  assert.equal(parseHookEvent(JSON.stringify(validEvent({ cwd: '/srv/project' }))).cwd, '/srv/project');
  assert.equal(parseHookEvent(JSON.stringify(validEvent())).cwd, null);
});
```

Create `output-path.test.mjs` with direct, hand-derived assertions:

```js
import assert from 'node:assert/strict';
import test from 'node:test';
import { resolveOutputPath } from '../../skills/command-driven-operations/scripts/command-guard/output-path.mjs';

test('literal output paths normalize against the hook cwd', () => {
  assert.equal(resolveOutputPath('./reports/status.json', { cwd: '/srv/ops' }), '/srv/ops/reports/status.json');
  assert.equal(resolveOutputPath('/var/tmp/status.json', { cwd: '/srv/ops' }), '/var/tmp/status.json');
  assert.equal(resolveOutputPath('reports\\status.json', { cwd: 'C:\\Ops', dialect: 'powershell' }), 'C:\\Ops\\reports\\status.json');
  assert.equal(resolveOutputPath('reports/status.json'), null);
});

test('only configured non-secret output variables resolve inside their roots', () => {
  const env = {
    OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR,OPS_EXPORT_DIR',
    OPS_OUTPUT_DIR: '/var/tmp/operations',
    OPS_EXPORT_DIR: '/srv/exports',
  };
  assert.equal(resolveOutputPath('$OPS_OUTPUT_DIR/report.json', { cwd: '/srv', env }), '/var/tmp/operations/report.json');
  assert.equal(resolveOutputPath('${OPS_EXPORT_DIR}/daily/report.json', { cwd: '/srv', env }), '/srv/exports/daily/report.json');
  assert.equal(resolveOutputPath('$env:OPS_OUTPUT_DIR\\report.json', { cwd: 'C:\\Ops', env: {
    OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: 'C:\\OpsOutput',
  }, dialect: 'powershell' }), 'C:\\OpsOutput\\report.json');
});

test('ambiguous unsafe or escaping output variables fail closed', () => {
  const env = { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: '/var/tmp/operations' };
  for (const operand of ['$DEST/report', '$HOME/report', '$OPS_OUTPUT_DIR/../escape', '${OPS_OUTPUT_DIR:-/tmp}/report', '$OPS_OUTPUT_DIR/$NAME']) {
    assert.equal(resolveOutputPath(operand, { cwd: '/srv', env }), null, operand);
  }
  for (const invalidEnv of [
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'API_TOKEN', API_TOKEN: '/tmp' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR,OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: '/tmp' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: 'relative' },
  ]) assert.equal(resolveOutputPath('$OPS_OUTPUT_DIR/report', { cwd: '/srv', env: invalidEnv }), null);
});
```

Cover zero/eight/nine configured names, malformed names, empty roots, Windows traversal, control characters, length bounds, exact-root destinations, and alternate slash forms in the same file.

- [x] **Step 2: Run the focused tests and witness RED**

```powershell
node --test tests/command-guard/contract.test.mjs tests/command-guard/output-path.test.mjs
```

Expected: module-not-found for `output-path.mjs` and missing `cwd` in the normalized event. The failures must be attributable to absent behavior, not test syntax.

- [x] **Step 3: Implement the bounded resolver and context plumbing**

Implement `output-path.mjs` around these exact constants and interface:

```js
import path from 'node:path';
import { LIMITS } from './limits.mjs';

const CONTROL = 'OPS_COMMAND_GUARD_OUTPUT_VARIABLES';
const MAX_OUTPUT_VARIABLES = 8;
const NAME = /^[A-Za-z_][A-Za-z0-9_]*$/u;
const FORBIDDEN_NAME = /(?:^|_)(?:TOKEN|SECRET|PASSWORD|PASSWD|AUTH|COOKIE|CREDENTIAL|KEY)(?:_|$)/iu;

export function resolveOutputPath(operand, { cwd = null, env = {}, dialect = 'bash' } = {}) {
  // Return a normalized absolute path or null. Query only CONTROL and the
  // names successfully parsed from CONTROL. Never enumerate env.
}
```

Use `path.posix` for slash-rooted operands and `path.win32` for drive/UNC or
PowerShell operands. Require `cwd` for literal relative paths. For variable
forms, require an absolute configured root and verify the resolved path equals
the root or starts with `root + separator`. Reject values or operands longer
than `LIMITS.tokenChars` and control characters.

Modify `contract.mjs` to return `cwd: value.cwd ?? null`. Change `lexCommand()`
in `policy.mjs` to return `{ lexed, dialect }`; use `bash` for the outer lexer
and `powershell` for the accepted wrapper. Call:

```js
const { lexed, dialect } = lexCommand(event.command);
composition = buildComposition(lexed);
const match = lookupFamily(stage, { cwd: event.cwd, env, dialect });
```

Change `evaluateHook()` to call `analyzeCommand(event, env)`. Preserve default
empty environment behavior for direct callers. Nested SSH catalogue analysis
must explicitly clear local path context:

```js
lookupFamily(composition.stages[0], { cwd: null, env: {}, dialect: 'bash', remote: true });
```

- [x] **Step 4: Add the resolver to critical and installed validation**

Add `output-path.mjs` to the critical include list in
`tests/run-command-guard-tests.mjs`. Confirm the installed-artifact validator's
recursive script comparison observes the new file; add an explicit expected
module assertion in `tests/command_guard_install_policy.py` if its inventory is
finite.

- [x] **Step 5: Run focused tests and verify GREEN**

```powershell
node --test tests/command-guard/contract.test.mjs tests/command-guard/output-path.test.mjs tests/command-guard/branches.test.mjs tests/command-guard/entrypoint.test.mjs
python tests/test-command-guard-install-policy.py
```

Expected: all selected tests pass and existing non-sink policy decisions are unchanged.

- [x] **Step 6: Evaluate the context/resolver commit checkpoint**

<!-- markdownlint-disable MD013 -->

```powershell
git diff --check
git status --short
git add -- skills/command-driven-operations/scripts/command-guard/output-path.mjs skills/command-driven-operations/scripts/command-guard/contract.mjs skills/command-driven-operations/scripts/command-guard/policy.mjs skills/command-driven-operations/scripts/command-guard/catalogue.mjs skills/command-driven-operations/scripts/validate-ops-command.mjs tests/command-guard/output-path.test.mjs tests/command-guard/contract.test.mjs tests/command-guard/helpers.mjs tests/run-command-guard-tests.mjs tests/command_guard_install_policy.py
git diff --cached --name-only
```

<!-- markdownlint-enable MD013 -->

Commit only if every staged hunk belongs solely to this task:

```powershell
git commit -m "fix: bind canonical output paths"
```

Otherwise unstage only these paths with `git restore --staged -- <paths>` and record the checkpoint as deferred; never discard worktree content.

### Task 2: Close HTTP option grammars and bind file effects

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/branches.test.mjs`
- Modify: `tests/test-loopback-http-fixture.py`

**Interfaces:**
- Private `parseCurlInvocation(words) -> invocation | null` replaces generic curl rescans.
- Private `parsePowerShellHttpInvocation(words) -> invocation | null` consumes case-insensitive PowerShell HTTP options.
- Private `classifyHttp(words, context) -> policy result | null` calls `resolveOutputPath()` and returns canonical remote-plus-local targets.

- [x] **Step 1: Add failing curl arity and cross-product tests**

Add a table-driven test to `security-regressions.test.mjs`:

```js
test('curl remote-name flags cannot hide bodies or uploads', () => {
  const bodies = ['-d value', '--data=value', '--data-raw value', '--json={}', '-F field=value'];
  for (const remoteName of ['-O', '--remote-name']) {
    for (const body of bodies) {
      const result = analyze(`curl ${remoteName} ${body} https://api.example.invalid/reload`, 'bypassPermissions', {
        cwd: '/work', env: {},
      });
      assert.equal(result.decision, 'ask', `${remoteName} ${body}`);
      assert.equal(result.risk, 'DISRUPTIVE_CHANGE');
      assert.ok(result.modifiers.includes('EXTERNAL_SIDE_EFFECT'));
      assert.ok(result.modifiers.includes('FILE_WRITE'));
      assert.ok(result.modifiers.includes('ALWAYS_ASK'));
    }
    for (const upload of ['-T payload.bin', '--upload-file=payload.bin']) {
      assert.equal(analyze(`curl ${remoteName} ${upload} https://api.example.invalid/items`, 'bypassPermissions', { cwd: '/work' }).decision, 'deny');
    }
  }
});
```

Update the local `analyze()` test helper to accept `{ cwd, env }`, put `cwd`
into `validEvent`, and pass `env` to `analyzeCommand`.

- [x] **Step 2: Add failing sink identity and confirmation tests**

Add exact expectations:

```js
test('HTTP sinks bind the normalized local destination and always ask', () => {
  const literal = analyze('curl -o reports/status.json https://api.example.invalid/reports/current', 'bypassPermissions', { cwd: '/srv/ops' });
  assert.equal(literal.decision, 'ask');
  assert.equal(literal.target, 'GET /reports/current -> file:/srv/ops/reports/status.json');
  assert.deepEqual(literal.modifiers.sort(), ['ALWAYS_ASK', 'FILE_WRITE']);

  const env = { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: '/var/tmp/operations' };
  const configured = analyze('curl -o "$OPS_OUTPUT_DIR/report.json" https://api.example.invalid/reports/current', 'bypassPermissions', { cwd: '/srv/ops', env });
  assert.equal(configured.target, 'GET /reports/current -> file:/var/tmp/operations/report.json');
  assert.equal(configured.decision, 'ask');

  assert.equal(analyze('curl -o "$DEST/report.json" https://api.example.invalid/reports/current', 'bypassPermissions', { cwd: '/srv/ops', env }).decision, 'deny');
});
```

Add equivalent PowerShell assertions for literal and configured
`$env:OPS_OUTPUT_DIR` paths. Add negative cases for missing `cwd`, repeated
sinks, unknown options, empty URL basename, `..`, encoded separators,
remote-header-name, nested variables, and output-root override attempts.
Update every pre-existing relative sink assertion to provide a literal `cwd`;
do not weaken the new missing-`cwd` denial to preserve old test setup.

- [x] **Step 3: Run focused tests and witness RED**

```powershell
node --test --test-name-pattern="remote-name|HTTP sinks" tests/command-guard/security-regressions.test.mjs
```

Expected: the reproduced commands return `allow/LOW_RISK_CHANGE`, dynamic sinks
remain accepted, and canonical targets are absent.

- [x] **Step 4: Implement the closed HTTP parsers**

Separate exact curl option sets in `catalogue.mjs`:

```js
const CURL_BODY_OPTIONS = ['-d', '--data', '--data-ascii', '--data-binary', '--data-raw', '--data-urlencode', '--json', '-F', '--form', '--form-string'];
const CURL_UPLOAD_OPTIONS = ['-T', '--upload-file'];
const CURL_SINK_VALUE_OPTIONS = ['-o', '--output', '-D', '--dump-header', '-c', '--cookie-jar', '--etag-save', '--trace'];
const CURL_SINK_FLAGS = ['-O', '--remote-name'];
const CURL_FLAGS = ['-s', '--silent', '-S', '--show-error', '-f', '--fail', '--fail-with-body', '-I', '--head', '-i', '--include', '-L', '--location', '--compressed', '--http1.1', '--http2', ...CURL_SINK_FLAGS];
```

`parseCurlInvocation()` must record entries and flags with correct arity,
support existing separated/equals/compact short value forms, retain repeatable
headers and body fragments, reject repeated singleton method/URL/sink groups,
and return exactly one literal URL. Do not derive semantics by rescanning raw
words after parsing.

Implement a case-insensitive PowerShell schema for `Uri`, `Method`, `Body`,
`InFile`, `OutFile`, headers, credentials, content type, timeouts, and the one
supported flag. Reject every other option and repeated singleton.

For a sink, resolve its operand with `resolveOutputPath()`. For remote-name,
derive and decode only a safe final URL filename. Compose:

```js
const target = sink
  ? `${method} ${parsed.pathname || '/'} -> file:${resolvedSink}`
  : parsed.pathname || '/';
const modifiers = [
  ...(sink ? ['FILE_WRITE', 'ALWAYS_ASK'] : []),
  ...(mutable ? ['EXTERNAL_SIDE_EFFECT'] : []),
];
```

Keep local request-file uploads denied. Preserve authenticated redirect and
credential-persistence denials.

- [x] **Step 5: Add a loopback semantic regression**

Extend `tests/test-loopback-http-fixture.py` to start the existing disposable
fixture, capability-probe `curl`/`curl.exe`, run:

```text
curl -sS -O -d action=restart http://127.0.0.1:<port>/reload
```

and assert the fixture records `POST /reload`. The test must use a temporary
working directory, synthetic body, loopback only, and remove the derived file.
If curl is unavailable, report an explicit capability skip while retaining the
mandatory parser matrix.

- [x] **Step 6: Run HTTP tests and verify GREEN**

```powershell
node --test tests/command-guard/security-regressions.test.mjs tests/command-guard/policy.test.mjs tests/command-guard/branches.test.mjs
python tests/test-loopback-http-fixture.py
```

Expected: every body form is classified as mutable despite remote-name, every
upload remains denied, all sinks ask in both mode families, and existing GET,
HEAD, DELETE, credential, redirect, route, and trust controls pass.

- [x] **Step 7: Evaluate the HTTP commit checkpoint**

Stage only the four listed implementation/test files, inspect staged names and
hunks, and commit if ownership is isolated:

```powershell
git commit -m "fix: close HTTP effects and sinks"
```

Otherwise defer the checkpoint without discarding any worktree content.

### Task 3: Close PostgreSQL and MySQL credential domains

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/command-guard/branches.test.mjs`

**Interfaces:**
- Private `parsePostgresInvocation(words) -> { query, host, port, user, database } | null`.
- Private `parseMySqlInvocation(words, executable) -> { query, host, port, user, database } | null`.
- Private `canonicalDatabaseEnvironment(family, invocation) -> string | null`.

- [x] **Step 1: Add failing repeated-selector and canonical-domain tests**

Add to `security-regressions.test.mjs`:

```js
test('database singleton selectors cannot diverge from the audited domain', () => {
  for (const command of [
    'PGPASSWORD=SYNTH_SECRET_pg psql -h audited.invalid -h effective.invalid -d app -c "SELECT 1"',
    'PGPASSWORD=SYNTH_SECRET_pg psql --host=audited.invalid -h effective.invalid -d app -c "SELECT 1"',
    'MYSQL_PWD=SYNTH_SECRET_mysql mysql -h audited.invalid --host=effective.invalid -D app -e "SHOW STATUS"',
    'MYSQL_PWD=SYNTH_SECRET_mysql mysql -P 3306 --port=3307 -h db.invalid -D app -e "SHOW STATUS"',
  ]) assert.equal(analyze(command).decision, 'deny', command);

  assert.equal(analyze('psql -h db.invalid -p 5433 -U appuser -d app -c "SELECT 1"').environment,
    'postgresql://appuser@db.invalid:5433/app');
  assert.equal(analyze('mysql -h db.invalid -P 3307 -u appuser -D app -e "SHOW STATUS"').environment,
    'mysql://appuser@db.invalid:3307/app');
});
```

Add cases for every same-alias and mixed-alias repetition, dynamic values,
invalid/overflow ports, missing query values, extra operands, config files,
service/login paths, sockets, protocols, and TLS/trust options.

- [x] **Step 2: Add a failing credential lifecycle test**

In `binding-store.test.mjs`, use `evaluateHook()` plus the matching successful
`evaluateApprovalHook()` event to approve a synthetic PostgreSQL credential for
`db-a.invalid:5432/app` and then request `db-b.invalid`, port 5433, another
user, and another database separately. Assert every changed domain asks rather
than returning `ALLOW_APPROVED_CREDENTIAL_BINDING`. Repeat the host transition
for MySQL.

- [x] **Step 3: Run database tests and witness RED**

```powershell
node --test --test-name-pattern="database singleton|database credential" tests/command-guard/security-regressions.test.mjs tests/command-guard/binding-store.test.mjs
```

Expected: repeated-host cases are accepted or bind the first value, canonical
domains omit selectors, and active bindings cross at least one changed scope.

- [x] **Step 4: Implement closed database parsers**

Use exact singleton maps:

```js
const POSTGRES_OPTIONS = new Map([
  ['-h', 'host'], ['--host', 'host'], ['-p', 'port'], ['--port', 'port'],
  ['-U', 'user'], ['--username', 'user'], ['-d', 'database'], ['--dbname', 'database'],
  ['-c', 'query'], ['--command', 'query'],
]);
const MYSQL_OPTIONS = new Map([
  ['-h', 'host'], ['--host', 'host'], ['-P', 'port'], ['--port', 'port'],
  ['-u', 'user'], ['--user', 'user'], ['-D', 'database'], ['--database', 'database'],
  ['-e', 'query'], ['--execute', 'query'],
]);
```

Consume separated, equals-attached long, and supported compact short forms.
Reject a group seen twice, an empty/dynamic value, unknown option, positional
psql/mysql operand, or unconsumed mysqladmin operand. For mysqladmin, accept
exactly one supported literal operation after its connection options.

Validate ports in `1..65535`. Canonicalize with explicit defaults:

```js
const defaults = family === 'POSTGRES'
  ? { scheme: 'postgresql', port: 5432 }
  : { scheme: 'mysql', port: 3306 };
return `${defaults.scheme}://${encodeURIComponent(user ?? 'default')}@${encodeURIComponent(host ?? 'default-host')}:${port ?? defaults.port}/${encodeURIComponent(database ?? 'default-db')}`;
```

Classify the parsed query with the existing finite SQL risk rules. Do not admit
service/config/socket/protocol/TLS options in this task.

- [x] **Step 5: Run database suites and verify GREEN**

```powershell
node --test tests/command-guard/security-regressions.test.mjs tests/command-guard/binding-store.test.mjs tests/command-guard/branches.test.mjs tests/command-guard/policy.test.mjs
```

Expected: duplicate selectors deny, domains contain every selector, credential
reuse cannot cross a domain, and existing bounded SQL risks remain unchanged.

- [x] **Step 6: Evaluate the database commit checkpoint**

Inspect exact staged hunks and commit only if isolated:

```powershell
git commit -m "fix: bind database client selectors"
```

Otherwise defer without resetting any worktree file.

### Task 4: Make Git branch deletion aliases equivalent

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/branches.test.mjs`

**Interfaces:**
- Private `parseGitBranch(words) -> { risk, target } | null` consumes the complete branch subgrammar.

- [x] **Step 1: Add failing alias-parity tests**

```js
test('every Git branch deletion alias is destructive and complete', () => {
  for (const command of [
    'git branch -d release', 'git branch -D release',
    'git branch --delete release', 'git branch --delete --force release',
    'git branch --force --delete release',
  ]) {
    for (const mode of ['default', 'bypassPermissions']) {
      const result = analyze(command, mode);
      assert.equal(result.decision, 'ask', `${mode}: ${command}`);
      assert.equal(result.risk, 'DESTRUCTIVE', command);
    }
  }
  for (const command of [
    'git branch --delete', 'git branch --delete --force',
    'git branch --delete --list release', 'git branch --delete $BRANCH',
    'git branch --delete release --unknown',
  ]) assert.equal(analyze(command).decision, 'deny', command);
});
```

Also assert `git branch`, `git branch --list`, literal branch creation, and
supported rename forms retain their expected risks.

- [x] **Step 2: Run the focused test and witness RED**

```powershell
node --test --test-name-pattern="Git branch deletion" tests/command-guard/security-regressions.test.mjs
```

Expected: both long deletion forms return `allow/LOW_RISK_CHANGE` in bypass.

- [x] **Step 3: Implement the closed branch subgrammar**

Before generic Git classification, parse `words[1] === 'branch'`. Treat the
mode flags as a finite mutually exclusive set. Allow deletion flags in either
documented long-order, normalize `-D` to delete plus force, require between one
and `LIMITS.fanOut` literal targets, and reject option-looking tokens after the
target list. Accept only these non-delete shapes: `branch`,
`branch --list [literal-pattern]`, `branch <literal-new> [literal-start]`, and
`branch -m|-M|--move <literal-old> <literal-new>`. Return `DESTRUCTIVE` for
deletion, `SAFE_READ_ONLY` for empty/list, and the existing change risk for
literal create/rename forms.

Remove branch deletion and generic branch fallback from the old regexes so one
parser owns every accepted branch form.

- [x] **Step 4: Run Git and catalogue suites and verify GREEN**

```powershell
node --test tests/command-guard/security-regressions.test.mjs tests/command-guard/policy.test.mjs tests/command-guard/branches.test.mjs
```

- [x] **Step 5: Evaluate the Git checkpoint**

Commit the isolated Git parser/test hunks as:

```powershell
git commit -m "fix: classify Git branch deletion aliases"
```

or record the checkpoint as deferred if overlapping dirty hunks prevent safe isolation.

### Task 5: Make mutation witnesses executable and baseline-proven

**Files:**
- Rewrite: `tests/command-guard/mutation-witnesses.mjs`
- Rewrite: `tests/command-guard/mutation-invariant.test.mjs`
- Modify: `tests/command-guard/mutation-registry.test.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/run-mutations.mjs`
- Create: `tests/command-guard/run-mutation-witness.mjs`
- Create: `tests/command-guard/mutation-protocol.mjs`
- Create: `tests/command-guard/mutation-protocol.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`

**Interfaces:**
- `MUTATION_WITNESSES: Readonly<Record<string, async ({ root, mutationId }) => void>>` is the single witness registry.
- `run-mutation-witness.mjs <id> <scripts-root>` exits `0` on invariant success, `42` plus `WITNESS_ASSERTION:<id>` only on Node assertion failure, and `2` on infrastructure/configuration failure.
- `interpretWitnessResult(result, id, phase) -> 'passed' | 'killed'` rejects every other status/marker combination.

- [x] **Step 1: Add failing mutation-protocol tests**

Create `mutation-protocol.test.mjs`:

```js
import assert from 'node:assert/strict';
import test from 'node:test';
import { interpretWitnessResult } from './mutation-protocol.mjs';

test('pristine witnesses must succeed', () => {
  assert.equal(interpretWitnessResult({ status: 0, stderr: '' }, 'X', 'baseline'), 'passed');
  for (const result of [{ status: 1, stderr: '' }, { status: 42, stderr: 'WITNESS_ASSERTION:X' }, { status: 2, stderr: 'import failed' }]) {
    assert.throws(() => interpretWitnessResult(result, 'X', 'baseline'));
  }
});

test('only the matching semantic assertion kills a mutant', () => {
  assert.equal(interpretWitnessResult({ status: 42, stderr: 'WITNESS_ASSERTION:X\n' }, 'X', 'mutant'), 'killed');
  for (const result of [
    { status: 0, stderr: '' },
    { status: 1, stderr: 'WITNESS_ASSERTION:X' },
    { status: 42, stderr: 'WITNESS_ASSERTION:Y' },
    { status: 2, stderr: 'SyntaxError' },
  ]) assert.throws(() => interpretWitnessResult(result, 'X', 'mutant'));
});
```

Add registry assertions using `Object.keys(MUTATION_WITNESSES)` instead of a
manually duplicated ID list.

- [x] **Step 2: Run protocol tests and witness RED**

```powershell
node --test tests/command-guard/mutation-protocol.test.mjs tests/command-guard/mutation-registry.test.mjs
```

Expected: module-not-found and missing executable-map failures.

- [x] **Step 3: Implement the witness map and child protocol**

Move every existing switch case into a named async function in
`MUTATION_WITNESSES`. Keep the dynamic module-root helpers in that module so
the same function runs against pristine and mutant copies.

Implement `run-mutation-witness.mjs`:

```js
import assert from 'node:assert/strict';
import { MUTATION_WITNESSES } from './mutation-witnesses.mjs';

const [id, root] = process.argv.slice(2);
const witness = MUTATION_WITNESSES[id];
if (!id || !root || !witness) process.exitCode = 2;
else {
  try {
    await witness({ root, mutationId: id });
    process.exitCode = 0;
  } catch (error) {
    if (error instanceof assert.AssertionError) {
      process.stderr.write(`WITNESS_ASSERTION:${id}\n`);
      process.exitCode = 42;
    } else {
      process.stderr.write(`WITNESS_INFRASTRUCTURE:${id}:${error?.name ?? 'Error'}\n`);
      process.exitCode = 2;
    }
  }
}
```

`mutation-invariant.test.mjs` loops all map entries against the pristine source
and has no skip. `run-mutations.mjs` first spawns every pristine witness and
requires `interpretWitnessResult(..., 'baseline') === 'passed'`; it then creates
each one-site mutant and requires the exact matching assertion marker with exit
42. A surviving mutant, crash, import failure, timeout, or wrong marker fails.

- [x] **Step 4: Register new behavior mutations before their witnesses**

Add exact one-site mutations and matching security predicate IDs for:

```text
CATALOGUE_CURL_REMOTE_NAME_ARITY
CATALOGUE_HTTP_SINK_ALWAYS_ASK
CATALOGUE_DATABASE_SELECTOR_UNIQUENESS
CATALOGUE_DATABASE_CANONICAL_ENVIRONMENT
CATALOGUE_GIT_LONG_DELETE
OUTPUT_PATH_ALLOWLIST
```

Run the registry/protocol test before adding their functions. Expected: exact
key-equality failure names all missing witnesses. Then add one witness function
per ID using the real policy or resolver and literal expected results.

- [x] **Step 5: Verify pristine baseline and every mutant**

```powershell
node --test tests/command-guard/mutation-protocol.test.mjs tests/command-guard/mutation-registry.test.mjs tests/command-guard/mutation-invariant.test.mjs
node tests/command-guard/run-mutations.mjs
```

Expected: every pristine witness passes; every registered mutant exits through
its own `WITNESS_ASSERTION:<id>`; the final killed count equals predicate,
mutation, and witness-map cardinality.

- [x] **Step 6: Evaluate the mutation checkpoint**

Stage only mutation protocol, registry, witnesses, new behavior mutations, and
their predicate IDs. Inspect every staged path and commit if separable:

```powershell
git commit -m "test: prove mutation witnesses from baseline"
```

Otherwise defer without modifying unrelated worktree state.

### Task 6: Add stable review evidence and operator documentation

**Files:**
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/executable-fixtures.test.mjs`
- Modify: `tests/command-guard/coverage-fixtures.mjs`
- Modify: `tests/command-guard/run-installed-corpus.mjs`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-07-29-p0-04-eighth-review-remediation-design.md`
- Modify: `docs/superpowers/plans/2026-07-29-p0-04-eighth-review-remediation.md`

**Interfaces:**
- Command fixtures may add `cwd` and `policyEnv` fields; source and installed runners must pass both to `analyzeCommand(event, policyEnv ?? {})`.
- RV-41 through RV-44 are source/installed operational fixtures; RV-45 is repository-only mutation protocol evidence.

- [x] **Step 1: Add stable operational fixtures**

Append at least these cases:

```js
{
  id: 'RV41-CURL-REMOTE-NAME-POST',
  command: 'curl -O -d action=restart https://api.example.invalid/reload',
  cwd: '/srv/ops',
  expectedDecision: 'ask',
  expectedRisk: 'DISRUPTIVE_CHANGE',
  expectedTarget: 'POST /reload -> file:/srv/ops/reload',
  expectedModifiers: ['ALWAYS_ASK', 'EXTERNAL_SIDE_EFFECT', 'FILE_WRITE'],
},
{
  id: 'RV42-POSTGRES-DUPLICATE-HOST',
  command: 'PGPASSWORD=SYNTH_SECRET_rv42 psql -h audited.invalid -h effective.invalid -d app -c "SELECT 1"',
  expectedDecision: 'deny',
  forbiddenText: 'SYNTH_SECRET_rv42',
},
{
  id: 'RV43-CONFIGURED-OUTPUT-PATH',
  command: 'curl -o "$OPS_OUTPUT_DIR/report.json" https://api.example.invalid/reports/current',
  cwd: '/srv/ops',
  policyEnv: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: '/var/tmp/operations' },
  expectedDecision: 'ask',
  expectedTarget: 'GET /reports/current -> file:/var/tmp/operations/report.json',
  expectedModifiers: ['ALWAYS_ASK', 'FILE_WRITE'],
},
{
  id: 'RV44-GIT-LONG-BRANCH-DELETE',
  command: 'git branch --delete --force release',
  expectedDecision: 'ask',
  expectedRisk: 'DESTRUCTIVE',
},
```

Extend both runners to assert target and sorted modifiers when declared.

- [x] **Step 2: Run source fixture tests and witness any runner gaps**

```powershell
node --test tests/command-guard/executable-fixtures.test.mjs tests/command-guard/coverage.test.mjs
```

Expected before runner changes: fixture metadata is ignored or expected target
assertions fail. After the minimal runner extension, every RV-01 through RV-44
fixture must execute exactly once.

- [x] **Step 3: Record the eighth independent-review disposition**

Add an eighth disposition with RV-41 through RV-45:

- RV-41: curl zero-argument flag arity hid body/upload semantics;
- RV-42: repeated database selectors broke credential domain binding;
- RV-43: HTTP local sinks lacked canonical path binding and mandatory confirmation;
- RV-44: long Git branch deletion aliases escaped destructive classification; and
- RV-45: mutation witnesses lacked a pristine baseline and typed failure protocol.

Mark each locally remediated with independent verification pending. Record RED
evidence and final counts only after Task 7 observes them.

- [x] **Step 4: Update ADR, README, changelog, specification, and plan**

Document:

- closed affected-client grammars and complete option consumption;
- `OPS_COMMAND_GUARD_OUTPUT_VARIABLES` syntax and its non-secret operator contract;
- canonical `METHOD path -> file:path` identity;
- `FILE_WRITE + ALWAYS_ASK` in every mode;
- complete PostgreSQL/MySQL domains and denied unmodelled selectors;
- Git deletion alias parity; and
- baseline-proven typed mutation witness failures.

Keep the release at `0.11.0`. Treat observed versions as evidence, never pins.
Mark every completed plan checkbox and explain any deferred commit checkpoint.

- [x] **Step 5: Validate documentation**

```powershell
python tests/validate-content.py
python tests/test-architecture-docs.py
git diff --check
```

- [x] **Step 6: Evaluate the evidence/documentation checkpoint**

Inspect exact staged paths and commit if safe:

```powershell
git commit -m "docs: record eighth review remediation"
```

Otherwise defer the combined evidence update until PR integration.

### Task 7: Execute the complete verification matrix

**Files:**
- Modify only when a gate reveals a requirement defect; return to the owning task's RED/GREEN cycle first.

**Interfaces:**
- Produces fresh evidence for the review record and the subsequent independent merge decision.

- [x] **Step 1: Run the complete native Node gate**

```powershell
node tests/run-command-guard-tests.mjs
```

Expected: all active tests pass, only intentionally declared skips remain,
every critical module including `catalogue.mjs` and `output-path.mjs` reaches
100 percent line/function/branch coverage, all pristine witnesses pass, and all
registered mutations are killed by their matching semantic assertion.

- [x] **Step 2: Run host syntax and Python gates**

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

Every command must exit zero. Do not start Claude or read provider credentials.

- [x] **Step 3: Run the Debian/WSL package gate with a capability-compatible Node**

```powershell
wsl -d Debian -- bash -lc "cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04-command-guard && env PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/local/bin:/usr/bin:/bin bash tests/validate-package.sh"
```

The path above is observed local evidence, not a project pin. If unavailable,
locate another Node runtime by probing the required native coverage flags.

- [x] **Step 4: Validate an isolated Nori-installed artifact without Claude**

In Debian WSL, create `WORK="$(mktemp -d "${TMPDIR:-/tmp}/p0-04-nori-install.XXXXXX")"`, resolve it with `readlink -f`, and verify the result remains under the resolved temporary parent. Set:

```bash
export HOME="$WORK/home"
export CLAUDE_CONFIG_DIR="$HOME/.claude"
export HISTFILE=/dev/null
```

Resolve `sks` or `nori-skillsets`, then run:

```bash
"$NORI_BIN" --install-dir "$CLAUDE_CONFIG_DIR" --agent claude-code link "$ROOT" --name senior-infra-ops-analyst
"$NORI_BIN" --install-dir "$CLAUDE_CONFIG_DIR" --agent claude-code switch senior-infra-ops-analyst --agent claude-code
python3 "$ROOT/tests/validate-installed-subagents.py" --installed-agents-dir "$INSTALLED_AGENTS_DIR" --installed-skills-dir "$INSTALLED_SKILLS_DIR"
node "$ROOT/tests/command-guard/run-installed-corpus.mjs" "$INSTALLED_SKILLS_DIR/command-driven-operations/scripts"
```

Compare every source script with its installed counterpart using `cmp -s`.
Expected: 12 subagents, 24 agent skills, 20 slash commands, every RV-01 through
RV-44 fixture passing, and byte-equivalent security-critical scripts. Remove
only the exact verified temporary path through an EXIT trap.

- [x] **Step 5: Run final hygiene checks**

```powershell
git diff --check origin/main
git status --short --untracked-files=all
rg -n -- "^- \[ \]" docs/superpowers/plans/2026-07-29-p0-04-eighth-review-remediation.md
```

Verify there are no retained coverage directories, mutation copies, loopback
outputs, audit/state artifacts, real credentials, unintended version pins, or
unchecked current-plan boxes.

- [x] **Step 6: Record exact observed evidence**

Replace provisional counts in the eighth review disposition and ADR with the
fresh Node test total, skip count, mutation total, installed fixture total, and
installed Nori inventory. Rerun documentation validators and `git diff --check`.

- [x] **Step 7: Request a new independent read-only review**

## Execution outcome

All tasks were completed through the final independent verification. Per-task
commit checkpoints were evaluated but intentionally deferred because this
worktree already contained overlapping remediation hunks from the same PR; a
single reviewed integration commit preserves the coherent final state. Final
evidence: 187 active Node tests with zero skips, 100 percent critical
line/function/branch coverage, 38 of 38 typed mutations, 76 source-to-installed
fixtures, the complete Debian/WSL package gate, host PowerShell syntax, and an
isolated Nori install with 12 subagents, 24 project skills, and 20 slash
commands. The final independent read-only review reported no Critical or
Important issue and returned Ready to merge.

The reviewer must inspect the complete current worktree, reproduce RV-41
through RV-45 through the real entrypoints, probe adjacent option compositions,
run the full relevant gates, and verify `git status` is unchanged. Do not merge
or publish until that review reports no Critical or Important issue.
