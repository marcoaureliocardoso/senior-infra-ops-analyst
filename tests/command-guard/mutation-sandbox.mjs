import { cp, mkdir } from 'node:fs/promises';
import path from 'node:path';

export async function copyMutationSandbox({ sourceScripts, sourceBrowserScripts, temporary }) {
  const root = path.join(temporary, 'command-driven-operations', 'scripts');
  await mkdir(root, { recursive: true });
  await cp(path.join(sourceScripts, 'command-guard'), path.join(root, 'command-guard'), { recursive: true });
  await cp(path.join(sourceScripts, 'validate-ops-command.mjs'), path.join(root, 'validate-ops-command.mjs'));
  await cp(sourceBrowserScripts, path.join(temporary, 'browser-operations', 'scripts'), { recursive: true });
  return root;
}
