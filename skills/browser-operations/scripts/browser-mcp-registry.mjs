import { normalizeOrigin } from './browser-contract.mjs';


const CORE_TOOL_SCHEMAS = Object.freeze({
  browser_navigate: Object.freeze(['url']),
  browser_snapshot: Object.freeze(['boxes', 'depth', 'filename', 'target']),
  browser_type: Object.freeze(['element', 'slowly', 'submit', 'target', 'text']),
  browser_click: Object.freeze(['button', 'doubleClick', 'element', 'modifiers', 'target']),
});

export const MCP_BROWSER_DESCRIPTORS = Object.freeze([
  Object.freeze({
    id: 'playwright-mcp-accessibility-core',
    runtimeIdentity: 'microsoft/playwright-mcp',
    interfaceRevision: 'accessibility-core',
    routeClass: 'CONTROLLED_BROWSER_MCP',
    toolSchemas: CORE_TOOL_SCHEMAS,
    effects: Object.freeze(['SENSITIVE_READ', 'INTERACTIVE_STATE']),
    enforcement: Object.freeze({
      preCall: true,
      topLevelOrigin: false,
      redirects: false,
      popups: false,
      artifacts: false,
    }),
  }),
]);


function result(state, reasonCode, values = {}) {
  return Object.freeze({ state, reasonCode, ...values });
}


function normalizedServerName(value) {
  if (typeof value !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,63}$/u.test(value)) return null;
  return value;
}


function exactToolSchemas(observation, descriptor) {
  if (!Array.isArray(observation.tools)) return false;
  const observed = new Map();
  for (const tool of observation.tools) {
    if (!tool || typeof tool.name !== 'string' || !Array.isArray(tool.inputKeys)) return false;
    if (observed.has(tool.name) || tool.inputKeys.some((key) => typeof key !== 'string')) return false;
    observed.set(tool.name, [...tool.inputKeys].sort());
  }
  return Object.entries(descriptor.toolSchemas).every(([name, inputKeys]) =>
    observed.has(name)
    && JSON.stringify(observed.get(name)) === JSON.stringify([...inputKeys].sort()));
}


function descriptorMatches(observation, approvedRuntime, descriptor) {
  return observation.serverName === approvedRuntime.serverName
    && observation.runtimeIdentity === descriptor.runtimeIdentity
    && observation.runtimeIdentity === approvedRuntime.runtimeIdentity
    && observation.configurationFingerprint === approvedRuntime.configurationFingerprint
    && observation.interfaceRevision === descriptor.interfaceRevision
    && exactToolSchemas(observation, descriptor);
}


export function matchBrowserMcpCapability(
  observation,
  approvedRuntime,
  registry = MCP_BROWSER_DESCRIPTORS,
) {
  const serverName = normalizedServerName(observation?.serverName);
  if (!serverName || !approvedRuntime || typeof approvedRuntime !== 'object' || !Array.isArray(registry)) {
    return result('AVAILABLE_UNRECOGNIZED', 'CAPABILITY_UNRECOGNIZED');
  }
  const matches = registry.filter((descriptor) =>
    descriptorMatches(observation, approvedRuntime, descriptor));
  if (matches.length === 0) {
    return result('AVAILABLE_UNRECOGNIZED', 'CAPABILITY_UNRECOGNIZED');
  }
  if (matches.length !== 1) return result('CONFLICT', 'CAPABILITY_CONFLICT');
  const descriptor = matches[0];
  return result('AVAILABLE_RECOGNIZED', 'CAPABILITY_RECOGNIZED', {
    descriptorId: descriptor.id,
    routeClass: descriptor.routeClass,
    serverName,
    toolPrefix: `mcp__${serverName}__`,
    effects: descriptor.effects,
    enforcement: descriptor.enforcement,
  });
}


function descriptorFor(capability) {
  if (!['AVAILABLE_RECOGNIZED', 'ACTIVE'].includes(capability?.state)) {
    throw new Error('MCP_CAPABILITY_UNRECOGNIZED');
  }
  const matches = MCP_BROWSER_DESCRIPTORS.filter(({ id }) => id === capability.descriptorId);
  if (matches.length !== 1) throw new Error('MCP_CAPABILITY_CONFLICT');
  return matches[0];
}


function exactInput(input, allowed, required) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('MCP_INPUT_INVALID');
  for (const key of Object.keys(input)) if (!allowed.includes(key)) throw new Error('MCP_INPUT_INVALID');
  for (const key of required) if (!Object.hasOwn(input, key)) throw new Error('MCP_INPUT_INVALID');
}


export function mapBrowserMcpCall(capability, call) {
  const descriptor = descriptorFor(capability);
  if (!call || typeof call.toolName !== 'string' || !call.toolName.startsWith(capability.toolPrefix)) {
    throw new Error('MCP_TOOL_UNRECOGNIZED');
  }
  const logicalName = call.toolName.slice(capability.toolPrefix.length);
  if (!Object.hasOwn(descriptor.toolSchemas, logicalName)) throw new Error('MCP_TOOL_UNRECOGNIZED');

  switch (logicalName) {
    case 'browser_navigate':
      exactInput(call.input, ['url'], ['url']);
      return Object.freeze({
        action: 'navigate', effect: 'INTERACTIVE_STATE',
        destinationOrigin: normalizeOrigin(call.input.url), sensitiveInputKeys: Object.freeze([]),
      });
    case 'browser_snapshot':
      exactInput(call.input, descriptor.toolSchemas.browser_snapshot, []);
      if (Object.hasOwn(call.input, 'filename')) throw new Error('MCP_ARTIFACT_UNBOUND');
      return Object.freeze({
        action: 'inspect', effect: 'SENSITIVE_READ', destinationOrigin: null,
        sensitiveInputKeys: Object.freeze([]),
      });
    case 'browser_type':
      exactInput(call.input, descriptor.toolSchemas.browser_type, ['target', 'text']);
      return Object.freeze({
        action: 'fill', effect: 'INTERACTIVE_STATE', destinationOrigin: null,
        sensitiveInputKeys: Object.freeze(['text']),
      });
    case 'browser_click':
      exactInput(call.input, descriptor.toolSchemas.browser_click, ['target']);
      return Object.freeze({
        action: 'click', effect: 'UNKNOWN', destinationOrigin: null,
        sensitiveInputKeys: Object.freeze([]),
      });
    default:
      throw new Error('MCP_TOOL_UNRECOGNIZED');
  }
}
