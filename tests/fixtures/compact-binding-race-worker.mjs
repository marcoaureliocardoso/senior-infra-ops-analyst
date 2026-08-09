import { existsSync, writeFileSync } from 'node:fs';

import {
  activatePendingBinding,
  invalidateSessionBindings,
} from '../../skills/command-driven-operations/scripts/command-guard/binding-store.mjs';


const [mode, stateDirectory, signalPath, releasePath] = process.argv.slice(2);
const env = { OPS_COMMAND_GUARD_STATE_DIR: stateDirectory };
const binding = {
  sessionId: 'compact-session',
  toolUseId: 'compact-tool',
  domain: 'https://api.example.invalid',
  identity: 'operator',
  transport: 'AUTHORIZATION',
  family: 'HTTP',
  targetClass: 'HTTP',
};

if (mode === 'activate') {
  activatePendingBinding(binding, env, 1_800_000_000_001, {
    afterRead() {
      writeFileSync(signalPath, 'ready', { flag: 'wx' });
      while (!existsSync(releasePath)) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5);
      }
    },
  });
} else if (mode === 'compact') {
  writeFileSync(signalPath, 'ready', { flag: 'wx' });
  invalidateSessionBindings(binding.sessionId, env);
} else {
  throw new Error('invalid race worker mode');
}
