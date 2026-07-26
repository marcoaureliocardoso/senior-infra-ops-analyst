import { BASH_OPERATORS } from '../../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { POLICY_IDS } from '../../skills/command-driven-operations/scripts/command-guard/catalogue.mjs';
import { GRAMMAR_PRODUCTIONS } from '../../skills/command-driven-operations/scripts/command-guard/composition.mjs';
import { CREDENTIAL_TRANSPORTS } from '../../skills/command-driven-operations/scripts/command-guard/credential-flow.mjs';
import { LIMITS } from '../../skills/command-driven-operations/scripts/command-guard/limits.mjs';
import { REASON_CODES } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { POWERSHELL_OPERATORS } from '../../skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs';

export const EDGE_CASE_IDS = Object.freeze([
  'QUOTED_SEPARATOR', 'UNMATCHED_QUOTE', 'DYNAMIC_SUBSTITUTION', 'EMPTY_STAGE',
  'REDIRECT_MISSING_TARGET', 'UNKNOWN_MODE', 'DUPLICATE_SECURITY_KEY', 'AUDIT_FAILURE',
]);

function casesFor(prefix, items, boundary = false) {
  return Object.fromEntries(items.map((item) => [item, {
    positive: [`${prefix}:${item}:positive`],
    boundary: boundary ? [`${prefix}:${item}:n-1`, `${prefix}:${item}:n`, `${prefix}:${item}:n+1`] : [],
    negative: [`${prefix}:${item}:negative`],
  }]));
}

export const COVERAGE_MANIFEST = Object.freeze({
  grammar: casesFor('grammar', GRAMMAR_PRODUCTIONS),
  bashOperators: casesFor('bash-operator', BASH_OPERATORS),
  powershellOperators: casesFor('powershell-operator', POWERSHELL_OPERATORS),
  commandFamilies: casesFor('policy', POLICY_IDS),
  reasonCodes: casesFor('reason', REASON_CODES),
  limits: casesFor('limit', Object.keys(LIMITS), true),
  credentialTransports: casesFor('credential', CREDENTIAL_TRANSPORTS),
  edgeCases: casesFor('edge', EDGE_CASE_IDS),
});

export function validateCoverageManifest(manifest = COVERAGE_MANIFEST) {
  const expected = {
    grammar: GRAMMAR_PRODUCTIONS,
    bashOperators: BASH_OPERATORS,
    powershellOperators: POWERSHELL_OPERATORS,
    commandFamilies: POLICY_IDS,
    reasonCodes: REASON_CODES,
    limits: Object.keys(LIMITS),
    credentialTransports: CREDENTIAL_TRANSPORTS,
    edgeCases: EDGE_CASE_IDS,
  };
  for (const [category, inventory] of Object.entries(expected)) {
    const entries = manifest[category] ?? {};
    for (const item of inventory) {
      const cases = entries[item];
      if (!cases?.positive?.length || !cases?.negative?.length) throw new Error(`orphan:${category}:${item}`);
      if (category === 'limits' && cases.boundary?.length !== 3) throw new Error(`orphan:${category}:${item}:boundary`);
    }
    for (const item of Object.keys(entries)) if (!inventory.includes(item)) throw new Error(`stale:${category}:${item}`);
  }
  return true;
}
