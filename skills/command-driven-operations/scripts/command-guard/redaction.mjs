import { createHash } from 'node:crypto';

const PATTERNS = [
  { kind: 'AUTHORIZATION', regex: /Authorization:\s*(?:Bearer|Basic)\s+([^\s"']+)/giu },
  { kind: 'AUTHORIZATION', regex: /(?:X-API-Key|PRIVATE-TOKEN):\s*([^\s"']+)/giu },
  { kind: 'COOKIE', regex: /(?:Cookie|Set-Cookie):\s*([^\r\n"']+)/giu },
  {
    kind: 'VARIABLE', regex: /(?:^|[\s;])([A-Za-z_][A-Za-z0-9_]*)="([^"]*)"/gu, valueGroup: 2,
    accept: (match) => /^(?:PGPASSWORD|MYSQL_PWD|SSHPASS)$/iu.test(match[1]) || /(?:^|_)(?:PASSWORD|PASS|TOKEN|SECRET|CREDENTIAL)(?:_|$)|(?:^|_)(?:API|ACCESS|PRIVATE)_KEY(?:_|$)/iu.test(match[1]),
  },
  {
    kind: 'VARIABLE', regex: /(?:^|[\s;])([A-Za-z_][A-Za-z0-9_]*)='([^']*)'/gu, valueGroup: 2,
    accept: (match) => /^(?:PGPASSWORD|MYSQL_PWD|SSHPASS)$/iu.test(match[1]) || /(?:^|_)(?:PASSWORD|PASS|TOKEN|SECRET|CREDENTIAL)(?:_|$)|(?:^|_)(?:API|ACCESS|PRIVATE)_KEY(?:_|$)/iu.test(match[1]),
  },
  {
    kind: 'VARIABLE', regex: /(?:^|[\s;])([A-Za-z_][A-Za-z0-9_]*)=((?:\\.|[^\s"'\\])+)/gu, valueGroup: 2,
    accept: (match) => /^(?:PGPASSWORD|MYSQL_PWD|SSHPASS)$/iu.test(match[1]) || /(?:^|_)(?:PASSWORD|PASS|TOKEN|SECRET|CREDENTIAL)(?:_|$)|(?:^|_)(?:API|ACCESS|PRIVATE)_KEY(?:_|$)/iu.test(match[1]),
  },
  { kind: 'FLAG', regex: /(?:--password|--passphrase|--token|--secret|--api-key|--access-key|--client-secret)(?:=|\s+)"([^"]*)"/giu },
  { kind: 'FLAG', regex: /(?:--password|--passphrase|--token|--secret|--api-key|--access-key|--client-secret)(?:=|\s+)'([^']*)'/giu },
  { kind: 'FLAG', regex: /(?:--password|--passphrase|--token|--secret|--api-key|--access-key|--client-secret)(?:=|\s+)((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'FLAG', regex: /\bredis-cli\b[^\r\n;&|]*\s-a(?:\s+)?((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'FLAG', regex: /\bmysql(?:admin)?\b[^\r\n;&|]*\s-p((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'QUERY', regex: /[?&](?:access_token|api_key|apikey|password|token|secret)=([^&#\s"']+)/giu },
  { kind: 'BASIC_AUTH', regex: /(?:-u|--user)\s+"[^\s:"']+:([^"]*)"/giu },
  { kind: 'BASIC_AUTH', regex: /(?:-u|--user)\s+'[^\s:"']+:([^']*)'/giu },
  { kind: 'BASIC_AUTH', regex: /(?:-u|--user)\s+[^\s:"']+:((?:\\.|[^\s"'\\])+)/giu },
  { kind: 'POWERSHELL_PLAINTEXT', regex: /ConvertTo-SecureString\s+["']([^"']+)["']\s+-AsPlainText/giu },
  { kind: 'URI_USERINFO', regex: /:\/\/[^\s:@/]+:([^\s@/]+)@/giu },
];

export function detectSensitiveSpans(text) {
  const spans = [];
  for (const { kind, regex, valueGroup = 1, accept = () => true } of PATTERNS) {
    regex.lastIndex = 0;
    for (const match of text.matchAll(regex)) {
      if (!accept(match)) continue;
      const value = match[valueGroup];
      const offset = value.length ? match[0].lastIndexOf(value) : match[0].length - 1;
      spans.push({ start: match.index + offset, end: match.index + offset + value.length, kind });
    }
  }
  spans.sort((a, b) => a.start - b.start);
  return spans.filter((span, index) => index === 0 || span.start >= spans[index - 1].end);
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
