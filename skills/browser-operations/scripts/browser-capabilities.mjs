import { EFFECT_CLASSES, ROUTE_CLASSES } from './browser-contract.mjs';


const EXECUTORS = new Set([
  'main', 'cloud-platform-operator', 'database-operator', 'diagnostic-operator',
  'kubernetes-operator', 'network-edge-operator', 'observability-sre',
  'release-cicd-operator',
]);
const READ_ONLY_ROLES = new Set(['audit-evidence-collector']);
const MUTABLE_EFFECTS = new Set([
  'INTERACTIVE_STATE', 'LOW_RISK_CHANGE', 'DISRUPTIVE_CHANGE',
  'DESTRUCTIVE_CHANGE', 'SENSITIVE_ARTIFACT',
]);
const ROUTE_RANK = new Map(ROUTE_CLASSES.map((routeClass, index) => [routeClass, index]));
const TOOL_SEARCH_MODES = new Set(['available-used', 'available-unused', 'unavailable']);
const MAX_CONTEXT_COUNT = 1_000_000;


function unavailable() {
  return Object.freeze({
    state: 'UNAVAILABLE',
    reasonCode: 'CAPABILITY_UNAVAILABLE',
    routeClass: null,
    adapterId: null,
  });
}


function sameDescriptor(observation, candidate) {
  return candidate
    && candidate.runtimeIdentity === observation.runtimeIdentity
    && candidate.interfaceRevision === observation.interfaceRevision
    && candidate.routeClass === observation.routeClass;
}


function enforcementSufficient(effects, enforcement) {
  if (!enforcement || enforcement.preCall !== true) return false;
  const mutable = effects.some((effect) => MUTABLE_EFFECTS.has(effect));
  if (mutable && (
    enforcement.topLevelOrigin !== true
    || enforcement.redirects !== true
    || enforcement.popups !== true
  )) return false;
  if (effects.includes('SENSITIVE_ARTIFACT') && enforcement.artifacts !== true) return false;
  return true;
}


export function classifyCapability(observation, registry, role) {
  if (!observation || observation.available !== true) return unavailable();
  if (!Array.isArray(registry)) throw new Error('INVALID_CAPABILITY_REGISTRY');
  const matches = registry.filter((candidate) => sameDescriptor(observation, candidate));
  if (matches.length === 0) {
    return Object.freeze({
      state: 'AVAILABLE_UNRECOGNIZED',
      reasonCode: 'CAPABILITY_UNRECOGNIZED',
      routeClass: observation.routeClass ?? null,
      adapterId: null,
    });
  }
  if (matches.length !== 1) {
    return Object.freeze({
      state: 'CONFLICT',
      reasonCode: 'CAPABILITY_CONFLICT',
      routeClass: observation.routeClass,
      adapterId: null,
    });
  }

  const match = matches[0];
  const common = {
    routeClass: match.routeClass,
    adapterId: match.id,
    effects: Object.freeze([...match.effects]),
    enforcement: Object.freeze({ ...match.enforcement }),
  };
  if (!EXECUTORS.has(role) && !READ_ONLY_ROLES.has(role)) {
    return Object.freeze({
      state: 'AVAILABLE_RECOGNIZED', reasonCode: 'ROLE_NOT_EXECUTOR', ...common,
    });
  }
  if (!enforcementSufficient(match.effects, match.enforcement)) {
    return Object.freeze({
      state: 'AVAILABLE_RECOGNIZED', reasonCode: 'ENFORCEMENT_INSUFFICIENT', ...common,
    });
  }
  if (
    observation.guardProof?.active !== true
    || typeof observation.settingsFingerprint !== 'string'
    || observation.guardProof.settingsFingerprint !== observation.settingsFingerprint
  ) {
    return Object.freeze({
      state: 'AVAILABLE_RECOGNIZED', reasonCode: 'GUARD_UNPROVEN', ...common,
    });
  }
  return Object.freeze({ state: 'ACTIVE', reasonCode: 'CAPABILITY_ACTIVE', ...common });
}


function roleAllows(role, effect) {
  if (EXECUTORS.has(role)) return true;
  return READ_ONLY_ROLES.has(role) && (effect === 'PUBLIC_READ' || effect === 'SENSITIVE_READ');
}


export function chooseBrowserRoute(effect, candidates, role) {
  if (!EFFECT_CLASSES.includes(effect) || effect === 'UNKNOWN') {
    return Object.freeze({ route: null, adapterId: null, reasonCode: 'NO_ENFORCEABLE_ROUTE' });
  }
  if (!roleAllows(role, effect)) {
    return Object.freeze({ route: null, adapterId: null, reasonCode: 'ROLE_NOT_EXECUTOR' });
  }
  if (!Array.isArray(candidates)) throw new Error('INVALID_CAPABILITY_CANDIDATES');
  const eligible = candidates.filter((candidate) =>
    candidate?.state === 'ACTIVE'
    && ROUTE_RANK.has(candidate.routeClass)
    && Array.isArray(candidate.effects)
    && candidate.effects.includes(effect)
    && enforcementSufficient([effect], candidate.enforcement));
  if (eligible.length === 0) {
    return Object.freeze({ route: null, adapterId: null, reasonCode: 'NO_ENFORCEABLE_ROUTE' });
  }
  eligible.sort((left, right) => ROUTE_RANK.get(left.routeClass) - ROUTE_RANK.get(right.routeClass));
  const bestRank = ROUTE_RANK.get(eligible[0].routeClass);
  const best = eligible.filter((candidate) => ROUTE_RANK.get(candidate.routeClass) === bestRank);
  if (best.length !== 1) {
    return Object.freeze({ route: null, adapterId: null, reasonCode: 'CAPABILITY_CONFLICT' });
  }
  return Object.freeze({
    route: best[0].routeClass,
    adapterId: best[0].adapterId,
    reasonCode: 'ROUTE_SELECTED',
  });
}


function contextPercent(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 100) {
    throw new Error('INVALID_CONTEXT_PERCENT');
  }
  return value;
}


function contextCount(value) {
  if (!Number.isSafeInteger(value) || value < 0 || value > MAX_CONTEXT_COUNT) {
    throw new Error('INVALID_CONTEXT_COUNT');
  }
  return value;
}


function contextSample(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('INVALID_CONTEXT_SAMPLE');
  }
  if (!TOOL_SEARCH_MODES.has(value.toolSearchMode)) throw new Error('INVALID_TOOL_SEARCH_MODE');
  return {
    usedPercent: contextPercent(value.usedPercent),
    skillCount: contextCount(value.skillCount),
    subagentCount: contextCount(value.subagentCount),
    schemaCount: contextCount(value.schemaCount),
    toolCount: contextCount(value.toolCount),
    toolSearchMode: value.toolSearchMode,
  };
}


export function summarizeContextDelta(before, after) {
  const left = contextSample(before);
  const right = contextSample(after);
  return Object.freeze({
    usedBefore: left.usedPercent,
    usedAfter: right.usedPercent,
    delta: right.usedPercent - left.usedPercent,
    skillCountBefore: left.skillCount,
    skillCountAfter: right.skillCount,
    subagentCountBefore: left.subagentCount,
    subagentCountAfter: right.subagentCount,
    schemaCountBefore: left.schemaCount,
    schemaCountAfter: right.schemaCount,
    toolCountBefore: left.toolCount,
    toolCountAfter: right.toolCount,
    toolSearchMode: right.toolSearchMode,
  });
}
