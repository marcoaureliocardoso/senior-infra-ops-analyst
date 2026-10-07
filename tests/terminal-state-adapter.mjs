// Private, passive acceptance-harness protocol. Never forward terminal replies.
import { createRequire } from 'node:module';
import { lstatSync, readFileSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const MAX_FRAME = 131072, MAX_FEED = 65536, MAX_CAPTURE = 8388608;
const REJECTED = 'TERMINAL_PROTOCOL_REJECTED';
const reject = () => { throw new Error(REJECTED); };
const require = createRequire(import.meta.url);

export function createStateEngine(moduleRoot) {
  let Terminal;
  try {
    if (!path.isAbsolute(moduleRoot) || realpathSync(moduleRoot) !== moduleRoot || !lstatSync(moduleRoot).isDirectory()) reject();
    const packageRoot = path.join(moduleRoot,'@xterm','headless');
    const metadata = path.join(packageRoot,'package.json');
    const implementation = path.join(packageRoot,'lib-headless','xterm-headless.js');
    for (const location of [packageRoot,metadata,implementation]) {
      if (realpathSync(location) !== location || lstatSync(location).isSymbolicLink()) reject();
    }
    if (!lstatSync(metadata).isFile() || lstatSync(metadata).size > 65536 || !lstatSync(implementation).isFile()) reject();
    const info = JSON.parse(readFileSync(metadata,'utf8'));
    if (info.name !== '@xterm/headless' || info.version !== '6.0.0' || info.main !== 'lib-headless/xterm-headless.js') reject();
    ({ Terminal } = require(implementation));
  } catch { throw new Error('TERMINAL_DEPENDENCY_UNAVAILABLE'); }
  const terminal = new Terminal({cols:120, rows:40, scrollback:1000,
    allowProposedApi:true, convertEol:false, logLevel:'off'});
  const counts = {primaryAttributes:0, secondaryAttributes:0, cursorPosition:0, status:0, other:0};
  terminal.onData(value => {
    const category = /^\x1b\[\?[0-9;]+c$/.test(value) ? 'primaryAttributes' :
      /^\x1b\[>[0-9;]+c$/.test(value) ? 'secondaryAttributes' :
      /^\x1b\[\??[0-9]+;[0-9]+R$/.test(value) ? 'cursorPosition' :
      /^\x1b\[[0-9]+n$/.test(value) ? 'status' : 'other';
    counts[category] = Math.min(MAX_CAPTURE, counts[category]+1);
  });
  terminal.onBinary(() => { counts.other = Math.min(MAX_CAPTURE,counts.other+1); });
  let queue = Promise.resolve(), pending = 0, total = 0, closed = false, failed = false;
  return {
    feed(bytes) {
      if (closed || failed || !(bytes instanceof Uint8Array) || bytes.length > MAX_FEED || total+bytes.length > MAX_CAPTURE) {
        failed = true;
        return Promise.reject(new Error(REJECTED));
      }
      const owned = Buffer.from(bytes);
      total += owned.length; pending++;
      const operation = queue.then(() => {
        if (closed || failed) reject();
        return new Promise(resolve => terminal.write(owned,resolve));
      }).catch(() => { failed = true; reject(); }).finally(() => {pending--;});
      queue = operation.catch(() => {});
      return operation;
    },
    snapshot() {
      if (closed || failed || pending) reject();
      const buffer = terminal.buffer.active;
      const rows = Array.from({length:40}, (_,y) => {
        const line = buffer.getLine(buffer.viewportY+y);
        return Array.from({length:120}, (_,x) => {
          const cell = line?.getCell(x);
          const text = cell?.getChars() || '', width = cell?.getWidth() ?? 1;
          if (text.length > 16 || ![0,1,2].includes(width) || (text && cell.isInvisible())) reject();
          return {text,width};
        });
      });
      const snapshot = {active:buffer.type, cursorX:buffer.cursorX, cursorY:buffer.cursorY,
        baseY:buffer.baseY, viewportY:buffer.viewportY, rows, replyCounts:{...counts}};
      if (Buffer.byteLength(JSON.stringify(snapshot)) > MAX_FRAME-128) reject();
      return snapshot;
    },
    close() {
      if (!closed) {closed = true; terminal.dispose();}
    },
  };
}

async function protocol(moduleRoot) {
  let state, lastId = 0, finished = false;
  let retained = Buffer.alloc(0);
  async function emit(record) {
    const data = JSON.stringify(record)+'\n';
    if (Buffer.byteLength(data)>MAX_FRAME) reject();
    await new Promise((resolve,rejectWrite) => process.stdout.write(data,error => error ? rejectWrite(error) : resolve()));
  }
  try {
    for await (const chunk of process.stdin) {
      let start = 0;
      while (start<chunk.length) {
        const end = chunk.indexOf(10,start);
        const stop = end<0 ? chunk.length : end;
        if (retained.length+stop-start>MAX_FRAME) reject();
        retained = Buffer.concat([retained,chunk.subarray(start,stop)]);
        start = end<0 ? chunk.length : end+1;
        if (end<0) continue;
        const raw = new TextDecoder('utf-8',{fatal:true}).decode(retained);
        retained = Buffer.alloc(0);
        const request = JSON.parse(raw);
        if (!request || Array.isArray(request) || typeof request !== 'object' || JSON.stringify(request)!==raw) reject();
        const {id,op} = request;
        if (!Number.isSafeInteger(id) || id<=lastId || id<=0 || !['init','feed','snapshot','close'].includes(op)) reject();
        const keys = Object.keys(request).sort().join(',');
        if (keys !== (op==='feed' ? 'data,id,op' : 'id,op')) reject();
        lastId = id;
        if (op==='init') {
          if (state) reject();
          state = createStateEngine(moduleRoot);
        } else {
          if (!state) reject();
          if (op==='feed') {
            if (typeof request.data!=='string') reject();
            const bytes = Buffer.from(request.data,'base64');
            if (bytes.toString('base64')!==request.data) reject();
            await state.feed(bytes);
          }
        }
        const reply = {id,ok:true};
        if (op==='snapshot') reply.snapshot = state.snapshot();
        if (op==='close') {state.close(); finished = true;}
        await emit(reply);
        if (finished) {
          if (start !== chunk.length) reject();
          return;
        }
      }
    }
    if (retained.length || !finished) reject();
  } catch(error) {
    const reason = error?.message==='TERMINAL_DEPENDENCY_UNAVAILABLE' ? error.message : REJECTED;
    try { await emit({id:0,ok:false,reason}); } catch {}
    process.exitCode = 2;
  } finally {
    state?.close(); process.stdin.destroy();
  }
}

if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  if (process.argv.length!==4 || process.argv[2]!=='--module-root') {
    process.stdout.write('{"id":0,"ok":false,"reason":"TERMINAL_PROTOCOL_REJECTED"}\n');
    process.exitCode = 2;
  } else await protocol(process.argv[3]);
}
