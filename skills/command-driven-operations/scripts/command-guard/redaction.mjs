import { createHash } from 'node:crypto';
import { lexBash } from './bash-lexer.mjs';

function isSensitiveVariable(name) {
  if (name.toUpperCase() === 'OPS_CREDENTIAL_IDENTITY') return false;
  return /^(?:PGPASSWORD|MYSQL_PWD|SSHPASS)$/iu.test(name) ||
    /(?:^|_)(?:PASSWORD|PASS|TOKEN|SECRET|CREDENTIAL)(?:_|$)|(?:^|_)(?:API|ACCESS|PRIVATE)_KEY(?:_|$)/iu.test(name);
}

function credentialHeaderName(name) {
  const normalized = name.trim().toLowerCase();
  return /(?:^|[-_])(?:authorization|auth|token|secret|credential|password|passphrase)(?:$|[-_])/u.test(normalized) ||
    /(?:^|[-_])(?:api|access|private)[-_]key(?:$|[-_])/u.test(normalized);
}

const PATTERNS = [
  {
    kind: 'AUTHORIZATION', regex: /\b([!#$%&'*+.^_`|~0-9A-Za-z-]+):\s*([^\r\n"']+)/gu,
    valueGroup: 2, accept: (match) => credentialHeaderName(match[1]),
  },
  { kind: 'COOKIE', regex: /(?:Cookie|Set-Cookie):\s*([^\r\n"']+)/giu },
  { kind: 'COOKIE', regex: /(?:^|\s)(?:-b|--cookie)(?:=|\s+)"([^"]*=[^"]*)"/giu },
  { kind: 'COOKIE', regex: /(?:^|\s)(?:-b|--cookie)(?:=|\s+)'([^']*=[^']*)'/giu },
  { kind: 'COOKIE', regex: /(?:^|\s)(?:-b|--cookie)(?:=|\s+)((?:\\.|[^\s"'\\])+=(?:\\.|[^\s"'\\])+)/giu },
  { kind: 'COOKIE', regex: /(?:^|\s)-b"([^"]*=[^"]*)"/giu },
  { kind: 'COOKIE', regex: /(?:^|\s)-b'([^']*=[^']*)'/giu },
  { kind: 'COOKIE', regex: /(?:^|\s)-b((?:\\.|[^\s"'\\])+=(?:\\.|[^\s"'\\])+)/giu },
  {
    kind: 'VARIABLE', regex: /(?:^|[\s;])([A-Za-z_][A-Za-z0-9_]*)="([^"]*)"/gu, valueGroup: 2, selectorGroup: 1,
    accept: (match) => isSensitiveVariable(match[1]),
  },
  {
    kind: 'VARIABLE', regex: /(?:^|[\s;])([A-Za-z_][A-Za-z0-9_]*)='([^']*)'/gu, valueGroup: 2, selectorGroup: 1,
    accept: (match) => isSensitiveVariable(match[1]),
  },
  {
    kind: 'VARIABLE', regex: /(?:^|[\s;])([A-Za-z_][A-Za-z0-9_]*)=((?:\\.|[^\s"'\\])+)/gu, valueGroup: 2, selectorGroup: 1,
    accept: (match) => isSensitiveVariable(match[1]),
  },
  { kind: 'FLAG', regex: /(?:--password|--pass|--passphrase|--token|--oauth2-bearer|--secret|--api-key|--access-key|--client-secret)(?:=|\s+)"([^"]*)"/giu },
  { kind: 'FLAG', regex: /(?:--password|--pass|--passphrase|--token|--oauth2-bearer|--secret|--api-key|--access-key|--client-secret)(?:=|\s+)'([^']*)'/giu },
  { kind: 'FLAG', regex: /(?:--password|--pass|--passphrase|--token|--oauth2-bearer|--secret|--api-key|--access-key|--client-secret)(?:=|\s+)((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'FLAG', regex: /\bredis-cli\b[^\r\n;&|]*\s-a=?"([^"]*)"/giu },
  { kind: 'FLAG', regex: /\bredis-cli\b[^\r\n;&|]*\s-a=?'([^']*)'/giu },
  { kind: 'FLAG', regex: /\bredis-cli\b[^\r\n;&|]*\s-a(?:\s+)?((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'FLAG', regex: /\bmysql(?:admin)?\b[^\r\n;&|]*\s-p((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'QUERY', regex: /[?&](?:access_token|api_key|apikey|password|token|secret)=([^&#\s"']+)/giu },
  { kind: 'BASIC_AUTH', regex: /(?:-u|--user)\s+"[^\s:"']+:([^"]*)"/giu },
  { kind: 'BASIC_AUTH', regex: /(?:-u|--user)\s+'[^\s:"']+:([^']*)'/giu },
  { kind: 'BASIC_AUTH', regex: /(?:-u|--user)\s+[^\s:"']+:((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'BASIC_AUTH', regex: /(?:^|\s)(?:-u|--user=)"[^\s:"']+:([^"]*)"/giu },
  { kind: 'BASIC_AUTH', regex: /(?:^|\s)(?:-u|--user=)'[^\s:"']+:([^']*)'/giu },
  { kind: 'BASIC_AUTH', regex: /(?:^|\s)(?:-u|--user=)[^\s:"']+:((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'POWERSHELL_PLAINTEXT', regex: /ConvertTo-SecureString\s+["']([^"']+)["']\s+-AsPlainText/giu },
  { kind: 'URI_USERINFO', regex: /:\/\/[^\s:@/]+:([^\s@/]+)@/giu },
];

function rawValueSpan(token, rawOffset, kind) {
  return { start: token.start + rawOffset, end: token.end, kind };
}

function headerKind(value) {
  const name = /^\s*([^:\s]+)\s*:/u.exec(value)?.[1];
  if (name && credentialHeaderName(name)) return 'AUTHORIZATION';
  if (/^(?:Cookie|Set-Cookie):/iu.test(value)) return 'COOKIE';
  return null;
}

function credentialOption(words, index, separated, attached) {
  const token = words[index];
  const exact = separated.get(token.cooked);
  if (exact) {
    const value = words[index + 1];
    return value ? { kind: exact, value: value.cooked, span: rawValueSpan(value, 0, exact) } : null;
  }
  for (const [prefix, kind] of attached) {
    if (token.cooked.startsWith(prefix) && token.cooked.length > prefix.length) {
      return { kind, value: token.cooked.slice(prefix.length), span: rawValueSpan(token, prefix.length, kind) };
    }
  }
  return null;
}

function tokenSensitiveSpans(text) {
  let tokens;
  try { ({ tokens } = lexBash(text)); } catch { return []; }
  const spans = [];
  let stageWords = [];
  const inspectStage = () => {
    if (!stageWords.length) return;
    const executableIndex = stageWords.findIndex(({ cooked }) => !/^[A-Za-z_][A-Za-z0-9_]*=/u.test(cooked));
    for (const token of stageWords.slice(0, executableIndex < 0 ? stageWords.length : executableIndex)) {
      const separator = token.raw.indexOf('=');
      const name = token.cooked.slice(0, token.cooked.indexOf('='));
      if (separator >= 0 && isSensitiveVariable(name) && separator + 1 < token.raw.length) {
        spans.push({ ...rawValueSpan(token, separator + 1, 'VARIABLE'), selector: name });
      }
    }
    if (executableIndex < 0) return;
    const executable = stageWords[executableIndex].cooked.toLowerCase();
    const words = stageWords.slice(executableIndex + 1);
    if (executable === 'redis-cli') {
      const separated = new Map([['-a', 'FLAG'], ['--pass', 'FLAG']]);
      const attached = [['-a=', 'FLAG'], ['--pass=', 'FLAG'], ['-a', 'FLAG']];
      for (let index = 0; index < words.length; index += 1) {
        const found = credentialOption(words, index, separated, attached);
        if (found) spans.push(found.span);
      }
    }
    if (executable === 'curl') {
      const separated = new Map([
        ['-b', 'COOKIE'], ['--cookie', 'COOKIE'], ['-u', 'BASIC_AUTH'], ['--user', 'BASIC_AUTH'],
        ['--oauth2-bearer', 'FLAG'], ['--token', 'FLAG'], ['-H', 'HEADER'], ['--header', 'HEADER'],
      ]);
      const attached = [
        ['--oauth2-bearer=', 'FLAG'], ['--cookie=', 'COOKIE'], ['--header=', 'HEADER'],
        ['--token=', 'FLAG'], ['--user=', 'BASIC_AUTH'], ['-b=', 'COOKIE'], ['-u=', 'BASIC_AUTH'],
        ['-H=', 'HEADER'], ['-b', 'COOKIE'], ['-u', 'BASIC_AUTH'], ['-H', 'HEADER'],
      ];
      for (let index = 0; index < words.length; index += 1) {
        const found = credentialOption(words, index, separated, attached);
        if (!found) continue;
        const kind = found.kind === 'HEADER' ? headerKind(found.value) : found.kind;
        const isLiteralCredential = kind === 'COOKIE' ? found.value.includes('=') :
          kind === 'BASIC_AUTH' ? found.value.includes(':') : kind !== null;
        if (isLiteralCredential) spans.push({ ...found.span, kind });
      }
    }
  };
  for (const token of tokens) {
    if (token.kind === 'operator') { inspectStage(); stageWords = []; }
    else if (token.kind === 'word') stageWords.push(token);
  }
  inspectStage();
  return spans;
}

export function detectSensitiveSpans(text) {
  const spans = tokenSensitiveSpans(text);
  for (const { kind, regex, valueGroup = 1, selectorGroup = null, accept = () => true } of PATTERNS) {
    regex.lastIndex = 0;
    for (const match of text.matchAll(regex)) {
      if (!accept(match)) continue;
      const value = match[valueGroup];
      const offset = value.length ? match[0].lastIndexOf(value) : match[0].length - 1;
      spans.push({
        start: match.index + offset, end: match.index + offset + value.length, kind,
        ...(selectorGroup === null ? {} : { selector: match[selectorGroup] }),
      });
    }
  }
  spans.sort((a, b) => a.start - b.start || b.end - a.end);
  const nonOverlapping = [];
  for (const span of spans) {
    if (!nonOverlapping.length || span.start >= nonOverlapping.at(-1).end) nonOverlapping.push(span);
  }
  return nonOverlapping;
}

export function redactText(text, spans = detectSensitiveSpans(text)) {
  let result = '';
  let cursor = 0;
  for (const span of spans) {
    result += text.slice(cursor, span.start) + `<redacted:${span.kind}>`;
    cursor = span.end;
  }
  return result + text.slice(cursor);
}

export function normalizeAndFingerprint(text, spans = detectSensitiveSpans(text)) {
  const normalized = redactText(text, spans).trim().replace(/\s+/gu, ' ');
  const fingerprint = createHash('sha256').update(normalized, 'utf8').digest('hex');
  return { normalized, fingerprint };
}
