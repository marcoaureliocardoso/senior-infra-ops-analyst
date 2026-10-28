import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MCP_BROWSER_DESCRIPTORS,
  mapBrowserMcpCall,
  matchBrowserMcpCapability,
} from '../../skills/browser-operations/scripts/browser-mcp-registry.mjs';


function approvedRuntime(overrides = {}) {
  return {
    serverName: 'playwright',
    runtimeIdentity: 'microsoft/playwright-mcp',
    configurationFingerprint: 'approved-config-a',
    ...overrides,
  };
}


function observation(overrides = {}) {
  return {
    serverName: 'playwright',
    runtimeIdentity: 'microsoft/playwright-mcp',
    configurationFingerprint: 'approved-config-a',
    interfaceRevision: 'accessibility-core',
    tools: [
      { name: 'browser_navigate', inputKeys: ['url'] },
      { name: 'browser_snapshot', inputKeys: ['boxes', 'depth', 'filename', 'target'] },
      { name: 'browser_type', inputKeys: ['element', 'slowly', 'submit', 'target', 'text'] },
      { name: 'browser_click', inputKeys: ['button', 'doubleClick', 'element', 'modifiers', 'target'] },
    ],
    annotations: { readOnlyHint: true },
    ...overrides,
  };
}


test('production registry recognizes one exact approved Playwright MCP core interface', () => {
  const result = matchBrowserMcpCapability(observation(), approvedRuntime());
  assert.equal(result.state, 'AVAILABLE_RECOGNIZED');
  assert.equal(result.descriptorId, 'playwright-mcp-accessibility-core');
  assert.equal(result.routeClass, 'CONTROLLED_BROWSER_MCP');
  assert.equal(MCP_BROWSER_DESCRIPTORS.length >= 1, true);
});


test('lookalike identity, unapproved configuration, and schema drift stay unrecognized', () => {
  for (const candidate of [
    observation({ runtimeIdentity: 'lookalike/playwright-mcp' }),
    observation({ serverName: 'lookalike-playwright' }),
    observation({ configurationFingerprint: 'different-config' }),
    observation({ tools: [{ name: 'browser_navigate', inputKeys: ['url', 'unsafeScript'] }] }),
  ]) {
    const result = matchBrowserMcpCapability(candidate, approvedRuntime());
    assert.equal(result.state, 'AVAILABLE_UNRECOGNIZED');
    assert.equal(result.reasonCode, 'CAPABILITY_UNRECOGNIZED');
  }
});


test('annotations cannot upgrade or alter recognition', () => {
  const falseHints = matchBrowserMcpCapability(
    observation({ annotations: { readOnlyHint: false, destructiveHint: true } }),
    approvedRuntime(),
  );
  const trueHints = matchBrowserMcpCapability(
    observation({ annotations: { readOnlyHint: true, destructiveHint: false } }),
    approvedRuntime(),
  );
  assert.deepEqual(falseHints, trueHints);
  assert.equal('annotations' in falseHints, false);
});


test('ambiguous descriptor matches fail closed', () => {
  const registry = [MCP_BROWSER_DESCRIPTORS[0], {
    ...MCP_BROWSER_DESCRIPTORS[0], id: 'duplicate-descriptor',
  }];
  const result = matchBrowserMcpCapability(observation(), approvedRuntime(), registry);
  assert.equal(result.state, 'CONFLICT');
  assert.equal(result.reasonCode, 'CAPABILITY_CONFLICT');
});


test('maps exact navigation and snapshot calls without retaining page data', () => {
  const capability = matchBrowserMcpCapability(observation(), approvedRuntime());
  assert.deepEqual(mapBrowserMcpCall(capability, {
    toolName: 'mcp__playwright__browser_navigate',
    input: { url: 'https://Router.Example.Invalid/status' },
  }), {
    action: 'navigate',
    effect: 'INTERACTIVE_STATE',
    destinationOrigin: 'https://router.example.invalid:443',
    sensitiveInputKeys: [],
  });
  assert.deepEqual(mapBrowserMcpCall(capability, {
    toolName: 'mcp__playwright__browser_snapshot', input: {},
  }), {
    action: 'inspect', effect: 'SENSITIVE_READ', destinationOrigin: null,
    sensitiveInputKeys: [],
  });
});


test('maps text entry structurally and never returns its value', () => {
  const capability = matchBrowserMcpCapability(observation(), approvedRuntime());
  const canary = 'DO_NOT_RETAIN_TYPED_SECRET';
  const result = mapBrowserMcpCall(capability, {
    toolName: 'mcp__playwright__browser_type',
    input: { element: 'Password', target: 'e7', submit: false, text: canary },
  });
  assert.deepEqual(result, {
    action: 'fill', effect: 'INTERACTIVE_STATE', destinationOrigin: null,
    sensitiveInputKeys: ['text'],
  });
  assert.doesNotMatch(JSON.stringify(result), new RegExp(canary, 'u'));
});


test('mutation-ambiguous click and unknown tools map to UNKNOWN or deny', () => {
  const capability = matchBrowserMcpCapability(observation(), approvedRuntime());
  assert.equal(mapBrowserMcpCall(capability, {
    toolName: 'mcp__playwright__browser_click',
    input: { element: 'Save', target: 'e9' },
  }).effect, 'UNKNOWN');
  assert.throws(() => mapBrowserMcpCall(capability, {
    toolName: 'mcp__playwright__browser_evaluate', input: { function: '() => 1' },
  }), /MCP_TOOL_UNRECOGNIZED/u);
});


test('maps the same approved descriptor after capability activation', () => {
  const capability = matchBrowserMcpCapability(observation(), approvedRuntime());
  const mapped = mapBrowserMcpCall({ ...capability, state: 'ACTIVE' }, {
    toolName: `${capability.toolPrefix}browser_snapshot`, input: {},
  });
  assert.equal(mapped.action, 'inspect');
  assert.equal(mapped.effect, 'SENSITIVE_READ');
});
