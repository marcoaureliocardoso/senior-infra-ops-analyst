import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const adapter = fileURLToPath(new URL('./terminal-state-adapter.mjs', import.meta.url));
const moduleRoot = process.env.P004B_TERMINAL_MODULE_ROOT;
const frame = (id, op, data) => JSON.stringify(data === undefined ? {id, op} : {id, op, data}) + '\n';
async function engine(t) {
  assert.ok(existsSync(adapter), 'state engine interface missing');
  assert.ok(moduleRoot, 'explicit test runtime required');
  const { createStateEngine } = await import('./terminal-state-adapter.mjs');
  const state = createStateEngine(moduleRoot);
  t.after(() => state.close());
  return state;
}
function protocol(input) {
  assert.ok(existsSync(adapter), 'state engine interface missing');
  const result = spawnSync(process.execPath, [adapter, '--module-root', moduleRoot], {
    input, encoding: 'utf8', timeout: 10000, maxBuffer: 256 * 1024,
    env: {PATH: process.env.PATH},
  });
  assert.equal(result.error, undefined);
  assert.equal(result.stderr.length, 0, 'helper must not emit stderr');
  return {status: result.status, records: result.stdout.trim().split('\n').filter(Boolean).map(JSON.parse)};
}
const row = (s,y) => s.rows[y].map(c => c.text || (c.width ? ' ' : '')).join('').trimEnd();

test('alternate_restore preserves primary cells and saved cursor', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('MAIN\x1b[?1049hALT'));
  assert.equal(e.snapshot().active, 'alternate');
  assert.equal(row(e.snapshot(),0), '    ALT');
  await e.feed(Buffer.from('\x1b[?1049l'));
  assert.equal(e.snapshot().active, 'normal');
  assert.equal(row(e.snapshot(),0), 'MAIN');
  assert.equal(e.snapshot().cursorX, 4);
});
test('cursor save/restore maps to actual cells', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('\x1b[2;3H\x1b7\x1b[4;7H\x1b8X'));
  const s = e.snapshot();
  assert.equal(s.cursorY, 1); assert.equal(s.cursorX, 3);
  assert.equal(s.rows[1][2].text, 'X');
});
test('restricted scroll region leaves outside rows unchanged', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('A\r\nB\r\nC\r\nD\x1b[2;3r\x1b[3;1H\n'));
  assert.deepEqual([0,1,2,3].map(y => row(e.snapshot(),y)), ['A','C','','D']);
});
test('last column wraps only after another printable cell', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('x'.repeat(120)));
  assert.equal(e.snapshot().cursorY, 0); assert.equal(e.snapshot().cursorX, 120);
  await e.feed(Buffer.from('Z'));
  assert.equal(e.snapshot().cursorY, 1); assert.equal(e.snapshot().rows[1][0].text, 'Z');
});
test('wide and combining characters preserve cell widths', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('界e\u0301'));
  const s = e.snapshot();
  assert.equal(s.rows[0][0].width, 2); assert.equal(s.rows[0][1].width, 0);
  assert.equal(s.rows[0][2].text, 'e\u0301'); assert.equal(s.cursorX, 3);
});
test('split_sequences_and_write_ack preserve every UTF8 and VT boundary', async t => {
  const bytes = Buffer.from('\x1b[?1049h界e\u0301\x1b7\x1b[4;7HX\x1b8Y');
  const full = await engine(t); await full.feed(bytes);
  const expected = full.snapshot();
  for (let split=1; split<bytes.length; split++) {
    const e = await engine(t);
    await e.feed(bytes.subarray(0,split)); await e.feed(bytes.subarray(split));
    assert.deepEqual(e.snapshot(), expected);
    e.close();
  }
});
test('queued writes cannot provide a stale snapshot', async t => {
  const e = await engine(t);
  const first = e.feed(Buffer.from('A')), second = e.feed(Buffer.from('B'));
  assert.throws(() => e.snapshot(), {message:'TERMINAL_PROTOCOL_REJECTED'});
  await Promise.all([first,second]);
  assert.equal(row(e.snapshot(),0), 'AB');
});
test('snapshot rejects oversized combining cells rather than clipping', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('e'+'\u0301'.repeat(16)));
  assert.throws(() => e.snapshot(), {message:'TERMINAL_PROTOCOL_REJECTED'});
});
test('capture and feed bounds reject excess before parsing', async t => {
  const e = await engine(t);
  await assert.rejects(e.feed(Buffer.alloc(65537)), {message:'TERMINAL_PROTOCOL_REJECTED'});
  const bounded = await engine(t);
  for (let i=0;i<128;i++) await bounded.feed(Buffer.alloc(65536,0));
  await assert.rejects(bounded.feed(Buffer.from('x')), {message:'TERMINAL_PROTOCOL_REJECTED'});
});
test('passive replies are only closed numeric classifications', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('\x1b[c\x1b[6n\x1b[5n'));
  assert.deepEqual(e.snapshot().replyCounts,
    {primaryAttributes:1,secondaryAttributes:0,cursorPosition:1,status:1,other:0});
});
test('snapshot frame overflow rejects dense combining content', async t => {
  const e = await engine(t);
  const bytes = Buffer.from(('e'+'\u0301'.repeat(15)).repeat(4800));
  for (let offset=0;offset<bytes.length;offset+=65536) await e.feed(bytes.subarray(offset,offset+65536));
  assert.throws(() => e.snapshot(), {message:'TERMINAL_PROTOCOL_REJECTED'});
});
test('invisible nonempty cells cannot become visible input evidence', async t => {
  const e = await engine(t);
  await e.feed(Buffer.from('\x1b[8m❯\x1b[0m'));
  assert.throws(() => e.snapshot(), {message:'TERMINAL_PROTOCOL_REJECTED'});
});
test('protocol acknowledges parsed private snapshots and closes naturally', () => {
  const r = protocol(frame(1,'init')+frame(2,'feed',Buffer.from('界').toString('base64'))+
    frame(3,'snapshot')+frame(4,'close'));
  assert.equal(r.status,0); assert.deepEqual(r.records.map(x=>x.id),[1,2,3,4]);
  assert.equal(r.records[2].snapshot.rows[0][0].width,2);
  assert.equal(r.records[2].snapshot.cursorX,2);
});
for (const [name, request] of [
  ['duplicate', '{"id":2,"op":"snapshot","op":"close"}\n'],
  ['extra', '{"id":2,"op":"snapshot","extra":true}\n'],
  ['reused id', frame(1,'snapshot')],
  ['zero id', frame(0,'snapshot')],
  ['unsafe id', '{"id":9007199254740992,"op":"snapshot"}\n'],
  ['unknown op', frame(2,'arbitrary')],
  ['invalid base64', frame(2,'feed','%%%')],
  ['noncanonical base64', frame(2,'feed','YQ')],
  ['oversized feed', frame(2,'feed',Buffer.alloc(65537).toString('base64'))],
  ['unterminated', '{"id":2,"op":"snapshot"}'],
  ['oversized frame', 'x'.repeat(131073)],
]) test(`protocol_limits reject ${name} with a closed error`, () => {
  const r = protocol(frame(1,'init')+request);
  assert.equal(r.status,2);
  assert.deepEqual(r.records.at(-1), {id:0,ok:false,reason:'TERMINAL_PROTOCOL_REJECTED'});
});
