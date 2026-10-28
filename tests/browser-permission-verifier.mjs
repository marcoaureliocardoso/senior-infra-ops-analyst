import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { lexBash } from '../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { buildComposition } from '../skills/command-driven-operations/scripts/command-guard/composition.mjs';
import { parseRunnerArgs } from '../skills/browser-operations/scripts/browser-runner.mjs';


const CLOSED = Object.freeze({
  verified: false,
  reasonCode: 'P004B_PERMISSION_MISMATCH',
  phase: null,
  decision: null,
  invocationFingerprint: null,
  operationId: null,
  expectedEffect: null,
  executionSteps: 0,
  validationSteps: 0,
});
const EXPECTED_KEYS = Object.freeze([
  'phase', 'decision', 'runnerPath', 'operationId', 'sessionId', 'runNonce', 'origin',
]);
const REQUEST_KEYS = Object.freeze(['tool_name', 'input']);
const INPUT_KEYS = Object.freeze(['command']);
const MAX_COMMAND_CHARS = 65_536;


function exactKeys(value, keys) {
  return value !== null
    && typeof value === 'object'
    && !Array.isArray(value)
    && Object.keys(value).length === keys.length
    && keys.every((key) => Object.hasOwn(value, key));
}


function same(value, expected) {
  return JSON.stringify(value) === JSON.stringify(expected);
}


function authentication(origin) {
  return [
    { step: 'navigate', origin },
    {
      step: 'click', origin, locatorRole: 'link', locatorName: 'Login',
      effect: 'INTERACTIVE_STATE',
    },
    {
      step: 'fill', origin, locatorRole: 'textbox', locatorName: 'Password',
      valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD', valueClass: 'credential',
    },
    {
      step: 'click', origin, locatorRole: 'button', locatorName: 'Continue',
      effect: 'INTERACTIVE_STATE',
    },
    {
      step: 'fill', origin, locatorRole: 'textbox', locatorName: 'Code',
      valueRef: 'env:OPS_BROWSER_VALUE_TOTP', valueClass: 'credential',
    },
    {
      step: 'click', origin, locatorRole: 'button', locatorName: 'Verify',
      effect: 'INTERACTIVE_STATE',
    },
  ];
}


function expectedWorkflow(phase, origin) {
  const auth = authentication(origin);
  const allow = phase === 'allow';
  return {
    executionSteps: allow ? [...auth, {
      step: 'select', origin, locatorRole: 'combobox', locatorName: 'WAN enabled',
      valueRef: 'env:OPS_BROWSER_VALUE_DISABLED', valueClass: 'configuration',
    }, {
      step: 'click', origin, locatorRole: 'button', locatorName: 'Save',
      effect: 'LOW_RISK_CHANGE',
    }] : [...auth, {
      step: 'click', origin, locatorRole: 'button', locatorName: 'Rollback',
      effect: 'LOW_RISK_CHANGE',
    }],
    validationSteps: [...auth, {
      step: 'inspect', origin, locatorRole: 'status', locatorName: 'Saved state',
      predicate: 'text-equals',
      expectedRef: allow
        ? 'env:OPS_BROWSER_VALUE_EXPECTED_FALSE'
        : 'env:OPS_BROWSER_VALUE_EXPECTED_TRUE',
      expectRef: 'interface-state',
    }],
  };
}


function validExpected(expected, now) {
  if (!exactKeys(expected, EXPECTED_KEYS) || !Number.isSafeInteger(now) || now < 0) return false;
  if (!['allow', 'deny'].includes(expected.phase) || expected.decision !== expected.phase) return false;
  for (const field of ['runnerPath', 'operationId', 'sessionId', 'runNonce', 'origin']) {
    if (typeof expected[field] !== 'string' || expected[field].length < 1) return false;
  }
  return path.isAbsolute(expected.runnerPath);
}


function exactEnvelope(envelope, expected) {
  const actions = expected.phase === 'allow'
    ? ['navigate', 'fill', 'select', 'click', 'inspect']
    : ['navigate', 'fill', 'click', 'inspect'];
  return envelope.version === 1
    && envelope.operationId === expected.operationId
    && envelope.sessionId === expected.sessionId
    && envelope.role === 'network-edge-operator'
    && envelope.objectiveRef === expected.runNonce
    && envelope.target === 'loopback-router'
    && envelope.environment === 'test'
    && same(envelope.serviceOrigins, [expected.origin])
    && same(envelope.authOrigins, [expected.origin])
    && envelope.identityRef === 'vault:network-admin'
    && envelope.credentialTransport === 'vault'
    && envelope.permissionModeAtApproval === 'normal'
    && same(envelope.actions, actions)
    && envelope.expectedEffect === 'LOW_RISK_CHANGE'
    && envelope.risk === 'LOW_RISK_CHANGE'
    && same(envelope.modifiers, [])
    && envelope.preconditionRef === 'fixture-ready'
    && envelope.validationRef === 'interface-state'
    && envelope.compensationRef === 'fixture-rollback'
    && same(envelope.artifactPolicy, {
      enabled: false,
      types: [],
      purposeRef: 'none',
      sourceClasses: [],
      destinationClasses: [],
      maxItems: 0,
      maxBytes: 0,
      redaction: 'none',
      retentionSeconds: 0,
    });
}


export function verifyPermissionRequest(request, expected, now = Date.now()) {
  try {
    if (!validExpected(expected, now)
        || !exactKeys(request, REQUEST_KEYS)
        || request.tool_name !== 'Bash'
        || !exactKeys(request.input, INPUT_KEYS)
        || typeof request.input.command !== 'string'
        || request.input.command.length < 1
        || request.input.command.length > MAX_COMMAND_CHARS) return CLOSED;

    const composition = buildComposition(lexBash(request.input.command));
    if (composition.stages.length !== 1
        || composition.operators.length !== 0
        || composition.redirects.length !== 0) return CLOSED;
    const [stage] = composition.stages;
    const [node, runner, ...argv] = stage.argv;
    if (node !== 'node' || !path.isAbsolute(runner)
        || path.resolve(runner) !== path.resolve(expected.runnerPath)) return CLOSED;

    const parsed = parseRunnerArgs(argv, now);
    const workflow = expectedWorkflow(expected.phase, expected.origin);
    if (parsed.step !== 'workflow'
        || parsed.operationId !== expected.operationId
        || parsed.expiresInSeconds !== 600
        || !exactEnvelope(parsed.envelope, expected)
        || !same(parsed.executionSteps, workflow.executionSteps)
        || !same(parsed.validationSteps, workflow.validationSteps)) return CLOSED;

    return Object.freeze({
      verified: true,
      reasonCode: 'P004B_PERMISSION_EXACT',
      phase: expected.phase,
      decision: expected.decision,
      invocationFingerprint: parsed.invocationFingerprint,
      operationId: parsed.operationId,
      expectedEffect: parsed.envelope.expectedEffect,
      executionSteps: parsed.executionSteps.length,
      validationSteps: parsed.validationSteps.length,
    });
  } catch {
    return CLOSED;
  }
}


async function runCli() {
  const [phase, runnerPath, operationId, sessionId, runNonce, origin, decision, ...extra] = process.argv.slice(2);
  let bytes = 0;
  const chunks = [];
  for await (const chunk of process.stdin) {
    bytes += chunk.length;
    if (bytes > MAX_COMMAND_CHARS) {
      process.stdout.write(`${JSON.stringify(CLOSED)}\n`);
      return;
    }
    chunks.push(chunk);
  }
  let request = null;
  try {
    request = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    // The shared closed result below intentionally hides parser details.
  }
  const expected = extra.length === 0 ? {
    phase, decision, runnerPath, operationId, sessionId, runNonce, origin,
  } : null;
  process.stdout.write(`${JSON.stringify(verifyPermissionRequest(request, expected))}\n`);
}


if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  await runCli();
}
