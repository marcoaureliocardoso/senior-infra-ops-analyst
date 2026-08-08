#!/usr/bin/env node

import { pathToFileURL } from 'node:url';


const MAX_INPUT_BYTES = 64 * 1024;


export function renderStatusLine(value) {
  const context = value && typeof value === 'object' && !Array.isArray(value)
    ? value.context_window
    : null;
  const used = context?.used_percentage;
  const remaining = context?.remaining_percentage;
  const percent = Number.isFinite(used)
    ? used
    : Number.isFinite(remaining)
      ? 100 - remaining
      : null;
  return percent !== null && percent >= 0 && percent <= 100
    ? `ctx ${Math.round(percent)}%`
    : 'ctx --';
}


async function readBounded(input) {
  const chunks = [];
  let size = 0;
  for await (const chunk of input) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += bytes.length;
    if (size > MAX_INPUT_BYTES) throw new Error('status input exceeds limit');
    chunks.push(bytes);
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
}


export async function main({ input = process.stdin, output = process.stdout } = {}) {
  let rendered = 'ctx --';
  try {
    rendered = renderStatusLine(JSON.parse(await readBounded(input)));
  } catch {
    rendered = 'ctx --';
  }
  output.write(`${rendered}\n`);
  return 0;
}


if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
