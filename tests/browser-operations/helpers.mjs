export const NOW = Date.parse('2026-08-31T12:00:00Z');


export function browserEnvelope(overrides = {}) {
  return {
    version: 1,
    operationId: 'op-browser-001',
    sessionId: 'session-browser-001',
    role: 'main',
    objectiveRef: 'change-42-router-ui',
    target: 'edge-router-1',
    environment: 'production',
    serviceOrigins: ['https://router.example.invalid'],
    authOrigins: ['https://login.example.invalid'],
    identityRef: 'vault:network-admin',
    credentialTransport: 'vault',
    permissionModeAtApproval: 'normal',
    actions: ['authenticate', 'navigate', 'inspect', 'fill', 'click', 'validate'],
    expectedEffect: 'LOW_RISK_CHANGE',
    risk: 'LOW_RISK_CHANGE',
    modifiers: ['PRIVILEGED'],
    preconditionRef: 'router-reachable',
    validationRef: 'independent-interface-state',
    compensationRef: 'restore-prior-value',
    artifactPolicy: {
      enabled: false,
      types: [],
      purposeRef: 'none',
      sourceClasses: [],
      destinationClasses: [],
      maxItems: 0,
      maxBytes: 0,
      redaction: 'none',
      retentionSeconds: 0,
    },
    expiresAt: NOW + 600_000,
    ...overrides,
  };
}


export function capabilityFixture(overrides = {}) {
  return {
    state: 'ACTIVE',
    reasonCode: 'CAPABILITY_ACTIVE',
    adapterId: 'fixture-browser',
    routeClass: 'CONTROLLED_BROWSER_MCP',
    settingsFingerprint: 'settings-browser-a',
    descriptorId: 'playwright-mcp-accessibility-core',
    serverName: 'playwright',
    toolPrefix: 'mcp__playwright__',
    effects: ['SENSITIVE_READ', 'INTERACTIVE_STATE'],
    enforcement: {
      preCall: true,
      topLevelOrigin: true,
      redirects: true,
      popups: true,
      artifacts: true,
    },
    ...overrides,
  };
}


export function bindingFixture(overrides = {}) {
  return {
    active: true,
    operationId: 'op-browser-001',
    sessionId: 'session-browser-001',
    role: 'main',
    operationFingerprint: 'a'.repeat(64),
    adapterId: 'fixture-browser',
    routeClass: 'CONTROLLED_BROWSER_MCP',
    settingsFingerprint: 'settings-browser-a',
    permissionModes: ['normal', 'bypassPermissions'],
    outcome: 'READY',
    validationRequired: false,
    expiresAt: NOW + 600_000,
    ...overrides,
  };
}
