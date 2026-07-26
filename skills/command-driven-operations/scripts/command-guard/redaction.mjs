import { createHash } from 'node:crypto';

const PATTERNS = [
  { kind: 'AUTHORIZATION', regex: /Authorization:\s*(?:Bearer|Basic)\s+([^\s"']+)/giu },
  { kind: 'COOKIE', regex: /(?:Cookie|Set-Cookie):\s*([^\r\n"']+)/giu },
  { kind: 'VARIABLE', regex: /(?:PASSWORD|PASS|TOKEN|SECRET|API_KEY|CREDENTIAL)=([^\s"']+)/giu },
  { kind: 'FLAG', regex: /(?:--password|--token|--secret|--api-key)(?:=|\s+)([^\s"']+)/giu },
  { kind: 'URI_USERINFO', regex: /:\/\/[^\s:@/]+:([^\s@/]+)@/giu },
];

export function detectSensitiveSpans(text) {
  const spans = [];
  for (const { kind, regex } of PATTERNS) {
    regex.lastIndex = 0;
    for (const match of text.matchAll(regex)) {
      const value = match[1];
      const offset = match[0].lastIndexOf(value);
      spans.push({ start: match.index + offset, end: match.index + offset + value.length, kind });
    }
  }
  spans.sort((a, b) => a.start - b.start || b.end - a.end);
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
