#!/usr/bin/env node

import { parseRunnerArgs } from '../skills/browser-operations/scripts/browser-runner.mjs';


const MUTABLE_EFFECTS = new Set([
  'LOW_RISK_CHANGE', 'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE',
]);

try {
  const request = parseRunnerArgs(process.argv.slice(2), Date.now());
  if (request.step !== 'workflow') process.exit(2);
  const result = {
    operationId: request.operationId,
    sessionId: request.envelope.sessionId,
    invocationFingerprint: request.invocationFingerprint,
    expectedEffect: request.envelope.expectedEffect,
    executionSteps: request.executionSteps.length,
    validationSteps: request.validationSteps.length,
    authenticationRequested: request.executionSteps.some(({ step }) => step === 'fill'),
    mutationRequested: request.executionSteps.some(({ effect }) => MUTABLE_EFFECTS.has(effect)),
    validationRequested: request.validationSteps.at(-1)?.step === 'inspect',
  };
  process.stdout.write(`${JSON.stringify(result)}\n`);
} catch {
  process.exit(2);
}
