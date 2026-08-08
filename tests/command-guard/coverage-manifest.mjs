import { BASH_OPERATORS } from '../../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { POLICY_IDS } from '../../skills/command-driven-operations/scripts/command-guard/catalogue.mjs';
import { GRAMMAR_PRODUCTIONS } from '../../skills/command-driven-operations/scripts/command-guard/composition.mjs';
import { CREDENTIAL_TRANSPORTS } from '../../skills/command-driven-operations/scripts/command-guard/credential-flow.mjs';
import { LIMITS } from '../../skills/command-driven-operations/scripts/command-guard/limits.mjs';
import { REASON_CODES } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { POWERSHELL_OPERATORS } from '../../skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs';
import { REVIEW_REGRESSION_FIXTURES } from './review-regression-fixtures.mjs';

export const EDGE_CASE_IDS = Object.freeze([
  'QUOTED_SEPARATOR', 'UNMATCHED_QUOTE', 'DYNAMIC_SUBSTITUTION', 'EMPTY_STAGE',
  'REDIRECT_MISSING_TARGET', 'UNKNOWN_MODE', 'DUPLICATE_SECURITY_KEY', 'AUDIT_FAILURE',
]);

function casesFor(category, items) {
  return Object.fromEntries(items.map((item) => [item, {
    executable: [`${category}:${item}:executable`],
  }]));
}

export const COVERAGE_MANIFEST = Object.freeze({
  grammar: casesFor('grammar', GRAMMAR_PRODUCTIONS),
  bashOperators: casesFor('bashOperators', BASH_OPERATORS),
  powershellOperators: casesFor('powershellOperators', POWERSHELL_OPERATORS),
  commandFamilies: casesFor('commandFamilies', POLICY_IDS),
  reasonCodes: casesFor('reasonCodes', REASON_CODES),
  limits: casesFor('limits', Object.keys(LIMITS)),
  credentialTransports: casesFor('credentialTransports', CREDENTIAL_TRANSPORTS),
  edgeCases: casesFor('edgeCases', EDGE_CASE_IDS),
  reviewRegressions: Object.fromEntries(
    REVIEW_REGRESSION_FIXTURES.map(({ id }) => [id, { executable: [`reviewRegressions:${id}:executable`] }]),
  ),
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
    reviewRegressions: REVIEW_REGRESSION_FIXTURES.map(({ id }) => id),
  };
  for (const [category, inventory] of Object.entries(expected)) {
    const entries = manifest[category] ?? {};
    for (const item of inventory) {
      const cases = entries[item];
      if (cases?.executable?.length !== 1 || cases.executable[0] !== `${category}:${item}:executable`) {
        throw new Error(`orphan:${category}:${item}`);
      }
    }
    for (const item of Object.keys(entries)) if (!inventory.includes(item)) throw new Error(`stale:${category}:${item}`);
  }
  return true;
}
