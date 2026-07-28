import { LIMITS } from './limits.mjs';

const UNSUPPORTED = [/\$\(/u, /\bInvoke-Expression\b/iu, /\s-[Ee]ncodedCommand\b/u, /--%/u, /[{}]/u];
const UNQUOTED_DYNAMIC = new Set(['(', ')', '[', ']', '&']);
export const POWERSHELL_OPERATORS = Object.freeze(['&&', '||', '>>', '*>', '2>', '|', ';', '\n', '>']);

export function lexPowerShell(command, limits = LIMITS) {
  for (const pattern of UNSUPPORTED) if (pattern.test(command)) throw new Error('unsupported PowerShell construct');
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(command)) throw new Error('control character is unsupported');
  const tokens = [];
  let raw = '';
  let cooked = '';
  let start = 0;
  let quote = null;
  let escaped = false;
  const flush = (end) => {
    if (!raw) return;
    tokens.push({ kind: 'word', raw, cooked, quote, start, end });
    raw = ''; cooked = ''; quote = null;
  };
  for (let index = 0; index < command.length;) {
    const character = command[index];
    if (escaped) { raw += character; cooked += character; escaped = false; index += 1; continue; }
    if (character === '`' && quote !== 'single') { if (!raw) start = index; raw += character; escaped = true; index += 1; continue; }
    if (character === "'" || character === '"') {
      if (!raw) start = index;
      const expected = character === "'" ? 'single' : 'double';
      if (quote === null) { quote = expected; raw += character; index += 1; continue; }
      if (quote === expected) { raw += character; quote = null; index += 1; continue; }
      raw += character; cooked += character; index += 1; continue;
    }
    if (quote !== null) { raw += character; cooked += character; index += 1; continue; }
    if (/\s/u.test(character) && character !== '\n') { flush(index); index += 1; continue; }
    const operator = POWERSHELL_OPERATORS.find((candidate) => command.startsWith(candidate, index));
    if (operator) {
      flush(index);
      tokens.push({ kind: operator.includes('>') ? 'redirect' : 'operator', raw: operator, cooked: operator, quote: null, start: index, end: index + operator.length });
      index += operator.length; continue;
    }
    if (UNQUOTED_DYNAMIC.has(character)) throw new Error('unsupported PowerShell construct');
    if (!raw) start = index;
    raw += character; cooked += character; index += 1;
  }
  if (escaped || quote !== null) throw new Error('unmatched quote or escape');
  flush(command.length);
  if (tokens.length > limits.tokens) throw new Error('token limit exceeded');
  const stages = 1 + tokens.filter(({ kind }) => kind === 'operator').length;
  if (stages > limits.stages) throw new Error('stage limit exceeded');
  return Object.freeze({ profile: 'powershell', tokens: Object.freeze(tokens), unsupported: [] });
}
