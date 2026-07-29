import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveOutputPath } from '../../skills/command-driven-operations/scripts/command-guard/output-path.mjs';

const configured = Object.freeze({
  OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR,OPS_EXPORT_DIR',
  OPS_OUTPUT_DIR: '/srv/output',
  OPS_EXPORT_DIR: '/srv/export',
});

test('resolves literal POSIX output paths against the hook cwd', () => {
  assert.equal(resolveOutputPath('reports/result.json', { cwd: '/srv/project' }), '/srv/project/reports/result.json');
  assert.equal(resolveOutputPath('/var/tmp/result.json', { cwd: '/srv/project' }), '/var/tmp/result.json');
  assert.equal(resolveOutputPath('./result.json', { cwd: '/srv/project' }), '/srv/project/result.json');
  assert.equal(resolveOutputPath('../result.json', { cwd: '/srv/project/work' }), '/srv/project/result.json');
  assert.equal(resolveOutputPath('result.json'), null);
});

test('resolves literal Windows output paths with Windows semantics', () => {
  assert.equal(
    resolveOutputPath('reports\\result.json', { cwd: 'C:\\work\\project', dialect: 'powershell' }),
    'C:\\work\\project\\reports\\result.json',
  );
  assert.equal(
    resolveOutputPath('D:\\exports\\result.json', { cwd: 'C:\\work', dialect: 'powershell' }),
    'D:\\exports\\result.json',
  );
  assert.equal(
    resolveOutputPath('\\\\server\\share\\result.json', { cwd: 'C:\\work', dialect: 'powershell' }),
    '\\\\server\\share\\result.json',
  );
});

test('resolves only configured Bash output variables beneath their roots', () => {
  assert.equal(resolveOutputPath('$OPS_OUTPUT_DIR/report.json', { env: configured }), '/srv/output/report.json');
  assert.equal(resolveOutputPath('${OPS_EXPORT_DIR}/nested/report.json', { env: configured }), '/srv/export/nested/report.json');
  assert.equal(resolveOutputPath('$OPS_OUTPUT_DIR', { env: configured }), '/srv/output');
  assert.equal(resolveOutputPath('${OPS_OUTPUT_DIR}', { env: configured }), '/srv/output');
});

test('resolves only configured PowerShell output variables beneath their roots', () => {
  const env = {
    OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR',
    OPS_OUTPUT_DIR: 'C:\\guard-output',
  };
  assert.equal(
    resolveOutputPath('$env:OPS_OUTPUT_DIR\\report.json', { env, dialect: 'powershell' }),
    'C:\\guard-output\\report.json',
  );
  assert.equal(resolveOutputPath('$env:OPS_OUTPUT_DIR', { env, dialect: 'powershell' }), 'C:\\guard-output');
});

test('denies unconfigured, ambiguous, nested, and escaping variable expressions', () => {
  const denied = [
    '$DEST/report.json', '$HOME/report.json', '${OPS_OUTPUT_DIR:-/tmp}/report.json',
    '${!OPS_OUTPUT_DIR}/report.json', '${OPS_OUTPUT_DIR/${X}/y}', '$OPS_OUTPUT_DIR/../escape.json',
    '$OPS_OUTPUT_DIR/../../srv/output-elsewhere/report.json', '$OPS_OUTPUT_DIR/$(id)',
    '$OPS_OUTPUT_DIR/*.json', '$OPS_OUTPUT_DIR/{a,b}.json', '$OPS_OUTPUT_DIR/[ab].json',
  ];
  for (const operand of denied) assert.equal(resolveOutputPath(operand, { env: configured }), null, operand);
  assert.equal(resolveOutputPath('$env:DEST\\report.json', { env: configured, dialect: 'powershell' }), null);
  assert.equal(resolveOutputPath('$env:OPS_OUTPUT_DIR\\..\\escape.json', {
    env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: 'C:\\guard-output' },
    dialect: 'powershell',
  }), null);
});

test('denies malformed or unsafe output-variable configuration', () => {
  const invalid = [
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: 'relative/root' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST,DEST', DEST: '/srv/output' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'BAD-NAME', 'BAD-NAME': '/srv/output' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_TOKEN', OPS_TOKEN: '/srv/output' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_SECRET_DIR', OPS_SECRET_DIR: '/srv/output' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_PASSWORD_FILE', OPS_PASSWORD_FILE: '/srv/output' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_AUTH_DIR', OPS_AUTH_DIR: '/srv/output' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_KEY_DIR', OPS_KEY_DIR: '/srv/output' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: '' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: '/srv/out\u0000put' },
    { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: '/srv/output\nnext' },
  ];
  for (const env of invalid) assert.equal(resolveOutputPath('$DEST/report.json', { env }), null);
});

test('enforces the zero-to-eight output-variable bound', () => {
  assert.equal(resolveOutputPath('$DEST/report.json', { env: {} }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', { env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: '' } }), null);

  const names = Array.from({ length: 8 }, (_, index) => `OPS_OUT_${index}`);
  const eight = { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: names.join(',') };
  for (const [index, name] of names.entries()) eight[name] = `/srv/output/${index}`;
  assert.equal(resolveOutputPath('$OPS_OUT_7/report.json', { env: eight }), '/srv/output/7/report.json');

  const nineNames = [...names, 'OPS_OUT_8'];
  const nine = { ...eight, OPS_COMMAND_GUARD_OUTPUT_VARIABLES: nineNames.join(','), OPS_OUT_8: '/srv/output/8' };
  assert.equal(resolveOutputPath('$OPS_OUT_7/report.json', { env: nine }), null);
});

test('denies dynamic or malformed literal operands and accepts alternate separators safely', () => {
  const denied = ['', '.', '..', '~', '~/report.json', '~operator/report.json', '$DEST', '$(id)', '`id`', 'report?.json', 'report*.json', 'a{b}.json', 'a[b].json', 'bad\u0000name'];
  for (const operand of denied) assert.equal(resolveOutputPath(operand, { cwd: '/srv/project' }), null, JSON.stringify(operand));

  const env = { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR', OPS_OUTPUT_DIR: 'C:\\guard-output' };
  assert.equal(
    resolveOutputPath('$env:OPS_OUTPUT_DIR/report.json', { env, dialect: 'powershell' }),
    'C:\\guard-output\\report.json',
  );
});

test('fails closed for invalid resolver context and root-escape edge branches', () => {
  assert.equal(resolveOutputPath(null), null);
  assert.equal(resolveOutputPath('report.json', { dialect: 'unknown', cwd: '/srv' }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', { env: null }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', { env: 42 }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', { env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 42 } }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', {
    env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: 42 },
  }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', {
    env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST' },
  }), null);
  assert.equal(resolveOutputPath('$DEST//outside/report.json', {
    env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: '/srv/output' },
  }), null);
  assert.equal(resolveOutputPath('$DEST/report\n.json', {
    env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: '/srv/output' },
  }), null);
  assert.equal(resolveOutputPath('$env:', {
    dialect: 'powershell', env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: 'C:\\output' },
  }), null);
  assert.equal(resolveOutputPath('$env:DEST/D:\\outside\\report.json', {
    dialect: 'powershell', env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: 'C:\\output' },
  }), null);
  assert.equal(resolveOutputPath('reports/status.json', { cwd: '/srv/ops', dialect: 'powershell' }), '/srv/ops/reports/status.json');
});

test('bounds operands, cwd, control names, and configured root values', () => {
  assert.equal(resolveOutputPath('x'.repeat(8193), { cwd: '/srv/project' }), null);
  assert.equal(resolveOutputPath('report.json', { cwd: `/${'x'.repeat(8193)}` }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', {
    env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'x'.repeat(513), DEST: '/srv/output' },
  }), null);
  assert.equal(resolveOutputPath('$DEST/report.json', {
    env: { OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'DEST', DEST: `/${'x'.repeat(8193)}` },
  }), null);
});
