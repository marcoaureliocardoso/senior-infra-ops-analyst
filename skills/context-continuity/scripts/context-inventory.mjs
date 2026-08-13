#!/usr/bin/env node

import { lstat, readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { parseStrictObject } from './settings.mjs';


const IDENTIFIER = /^[A-Za-z0-9._-]{1,128}$/u;
const PACKAGE_ID = /^[a-z0-9-]{1,128}$/u;
const MAX_COUNT = 1_000_000;
const FORBIDDEN_KEYS = new Set([
  'content', 'prompt', 'response', 'summary', 'transcript', 'tool_input',
  'tool_result', 'command', 'header', 'credential', 'secret', 'token',
]);


function bytes(text) {
  return Buffer.byteLength(text, 'utf8');
}


function boundedPackageId(value, label) {
  if (typeof value !== 'string' || !PACKAGE_ID.test(value)) {
    throw new Error(`invalid ${label} identifier`);
  }
  return value;
}


function boundedRuntimeId(value, fallback = 'unknown') {
  const selected = value ?? fallback;
  if (typeof selected !== 'string' || !IDENTIFIER.test(selected)) {
    throw new Error('invalid runtime identifier');
  }
  return selected;
}


function boundedCount(value, fallback = 0) {
  const selected = value ?? fallback;
  if (!Number.isSafeInteger(selected) || selected < 0 || selected > MAX_COUNT) {
    throw new Error('invalid runtime count');
  }
  return selected;
}


function boundedPercent(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 100) {
    throw new Error('invalid context percentage');
  }
  return value;
}


function frontmatterDescription(text) {
  const end = text.startsWith('---\n') ? text.indexOf('\n---\n', 4) : -1;
  if (end < 0) throw new Error('skill frontmatter missing');
  const match = text.slice(4, end).match(/^description:\s*(.+)$/mu);
  if (!match?.[1]) throw new Error('skill description missing');
  return match[1];
}


function frontmatterSkills(text) {
  const end = text.startsWith('---\n') ? text.indexOf('\n---\n', 4) : -1;
  if (end < 0) throw new Error('subagent frontmatter missing');
  const block = text.slice(4, end).match(/^skills:[ \t]*\r?\n((?:  - [a-z0-9-]+[ \t]*(?:\r?\n|$))+)/mu)?.[1];
  if (!block) throw new Error('subagent skills missing');
  return [...block.matchAll(/^  - ([a-z0-9-]+)[ \t]*$/gmu)].map((match) => match[1]);
}


async function safeText(target, label) {
  const info = await lstat(target);
  if (!info.isFile() || info.size > 2 * 1024 * 1024) throw new Error(`unsafe ${label}`);
  return readFile(target, 'utf8');
}


export async function collectStaticInventory(root) {
  const resolved = path.resolve(root);
  const rootInfo = await lstat(resolved);
  if (!rootInfo.isDirectory()) throw new Error('inventory root must be a directory');

  const rootText = await safeText(path.join(resolved, 'AGENTS.md'), 'root instructions');
  const skillItems = [];
  const skillBodies = new Map();
  const skillEntries = await readdir(path.join(resolved, 'skills'), { withFileTypes: true });
  for (const entry of skillEntries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (entry.isSymbolicLink()) throw new Error('linked skill entry is not allowed');
    if (!entry.isDirectory()) continue;
    const id = boundedPackageId(entry.name, 'skill');
    const text = await safeText(path.join(resolved, 'skills', id, 'SKILL.md'), `skill ${id}`);
    const bodyBytes = bytes(text);
    const descriptionBytes = bytes(frontmatterDescription(text));
    skillBodies.set(id, bodyBytes);
    skillItems.push(Object.freeze({ id, bodyBytes, descriptionBytes }));
  }

  const subagentItems = [];
  const subagentEntries = await readdir(path.join(resolved, 'subagents'), { withFileTypes: true });
  for (const entry of subagentEntries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (entry.isSymbolicLink()) throw new Error('linked subagent entry is not allowed');
    if (!entry.isDirectory()) continue;
    const id = boundedPackageId(entry.name, 'subagent');
    const directory = path.join(resolved, 'subagents', id);
    const metadata = parseStrictObject(
      await safeText(path.join(directory, 'nori.json'), `subagent manifest ${id}`),
    );
    if (metadata.name !== id || metadata.type !== 'subagent') {
      throw new Error(`invalid subagent manifest: ${id}`);
    }
    const text = await safeText(path.join(directory, 'SUBAGENT.md'), `subagent ${id}`);
    const preloadBytes = frontmatterSkills(text).reduce((total, skillId) => {
      if (!skillBodies.has(skillId)) throw new Error(`unregistered preloaded skill: ${skillId}`);
      return total + skillBodies.get(skillId);
    }, 0);
    subagentItems.push(Object.freeze({ id, definitionBytes: bytes(text), preloadBytes }));
  }

  return Object.freeze({
    schemaVersion: 1,
    rootInstructions: Object.freeze({ bytes: bytes(rootText), lines: rootText.split(/\r?\n/u).length }),
    skills: Object.freeze({
      count: skillItems.length,
      totalBodyBytes: skillItems.reduce((total, item) => total + item.bodyBytes, 0),
      totalDescriptionBytes: skillItems.reduce((total, item) => total + item.descriptionBytes, 0),
      items: Object.freeze(skillItems),
    }),
    subagents: Object.freeze({
      count: subagentItems.length,
      totalDefinitionBytes: subagentItems.reduce((total, item) => total + item.definitionBytes, 0),
      items: Object.freeze(subagentItems),
    }),
    mcp: Object.freeze({ packageServerCount: 0 }),
  });
}


export function normalizeRuntimeEvidence(events) {
  let beforePercent = null;
  let afterPercent = null;
  let compactionCount = 0;
  let visibleCountBefore = 0;
  let visibleCountAfter = 0;
  let searchAvailable = false;
  let searchObserved = false;
  let gatewayUnavailable = false;
  let connectedCount = 0;
  let visibleToolCount = 0;
  let mcpBeforePercent = null;
  let mcpAfterPercent = null;
  let reportedWindow = null;
  let observedWindow = null;
  let absoluteOverrideApplied = false;
  const rolePercentages = [];
  const skillPercentages = [];
  let resumeTasksObserved = false;
  let rewindTasksObserved = false;
  let rewindContextObserved = false;
  let rewindAuthorizationInvalidated = false;
  let isolatedClearObserved = false;
  const createdAt = new Map();
  const observedAt = new Map();
  const compactionCycles = [];
  let pendingPreCompact = null;
  const taskFamilies = new Set();
  let createdCount = 0;
  let completedCount = 0;
  let runtime = {
    claudeCode: 'unknown', nori: 'unknown', modelLabel: 'unknown',
    providerLabel: 'unknown', platform: 'unknown',
  };

  for (const [eventIndex, event] of events.entries()) {
    if (!event || typeof event !== 'object' || Array.isArray(event)) continue;
    switch (event.kind) {
      case 'context': {
        const percent = boundedPercent(event.percent);
        if (event.stage === 'before') beforePercent = percent;
        else if (event.stage === 'after') afterPercent = percent;
        break;
      }
      case 'context-role':
        rolePercentages.push(boundedPercent(event.percent));
        break;
      case 'skill-use':
        skillPercentages.push(boundedPercent(event.percent));
        break;
      case 'session':
        if (event.action === 'resume-tasks') resumeTasksObserved = true;
        else if (event.action === 'rewind-tasks') rewindTasksObserved = true;
        else if (event.action === 'rewind-context') rewindContextObserved = true;
        else if (event.action === 'rewind-authorization-invalid') rewindAuthorizationInvalidated = true;
        else if (event.action === 'clear-isolated') isolatedClearObserved = true;
        break;
      case 'compact':
        if (event.phase === 'PreCompact') pendingPreCompact = eventIndex;
        else if (event.phase === 'PostCompact' && pendingPreCompact !== null) {
          compactionCycles.push({ pre: pendingPreCompact, post: eventIndex });
          pendingPreCompact = null;
          compactionCount += 1;
        }
        break;
      case 'task': {
        const identifier = boundedRuntimeId(event.identifier);
        const family = boundedRuntimeId(event.family);
        taskFamilies.add(family === 'TodoWrite' ? 'TodoWrite' : 'TaskTools');
        if (event.action === 'created') {
          if (!createdAt.has(identifier)) createdAt.set(identifier, eventIndex);
          createdCount += 1;
        }
        else if (event.action === 'completed') completedCount += 1;
        else if (event.action === 'observed-after') {
          observedAt.set(identifier, [...(observedAt.get(identifier) ?? []), eventIndex]);
        }
        break;
      }
      case 'tool-snapshot':
        if (event.stage === 'before') visibleCountBefore = boundedCount(event.visibleCount);
        else if (event.stage === 'after') visibleCountAfter = boundedCount(event.visibleCount);
        break;
      case 'tool-search':
        searchObserved = true;
        searchAvailable = event.available === true;
        gatewayUnavailable = event.available === false && event.gatewayUnavailable === true;
        break;
      case 'mcp':
        connectedCount = boundedCount(event.connectedCount);
        visibleToolCount = boundedCount(event.visibleToolCount);
        mcpBeforePercent = event.beforePercent === undefined
          ? null : boundedPercent(event.beforePercent);
        mcpAfterPercent = event.afterPercent === undefined
          ? null : boundedPercent(event.afterPercent);
        break;
      case 'window':
        reportedWindow = boundedCount(event.reportedWindow);
        observedWindow = boundedCount(event.observedWindow);
        absoluteOverrideApplied = event.absoluteOverrideApplied === true;
        break;
      case 'runtime':
        runtime = {
          claudeCode: boundedRuntimeId(event.claudeCode),
          nori: boundedRuntimeId(event.nori),
          modelLabel: boundedRuntimeId(event.modelLabel),
          providerLabel: boundedRuntimeId(event.providerLabel),
          platform: boundedRuntimeId(event.platform),
        };
        break;
      default:
        break;
    }
  }

  const toolFamily = taskFamilies.size === 0 ? 'NOT_OBSERVED'
    : taskFamilies.size === 1 ? [...taskFamilies][0] : 'MixedNativeTasks';
  const reasonCode = searchAvailable ? 'TOOL_SEARCH_AVAILABLE'
    : gatewayUnavailable ? 'TOOL_SEARCH_UNAVAILABLE_GATEWAY'
      : 'TOOL_SEARCH_NOT_OBSERVED';
  const windowReasonCode = reportedWindow === null || observedWindow === null
    ? 'WINDOW_REPORTING_NOT_OBSERVED'
    : reportedWindow === observedWindow
      ? 'WINDOW_REPORTING_CONSISTENT' : 'WINDOW_REPORTING_DIVERGENCE';
  return Object.freeze({
    schemaVersion: 1,
    context: Object.freeze({
      beforePercent,
      afterPercent,
      deltaPercent: beforePercent === null || afterPercent === null ? null : afterPercent - beforePercent,
      compactionCount,
      roleCount: rolePercentages.length,
      rolePercentMin: rolePercentages.length === 0 ? null : Math.min(...rolePercentages),
      rolePercentMax: rolePercentages.length === 0 ? null : Math.max(...rolePercentages),
      skillUseCount: skillPercentages.length,
      skillPercentMin: skillPercentages.length === 0 ? null : Math.min(...skillPercentages),
      skillPercentMax: skillPercentages.length === 0 ? null : Math.max(...skillPercentages),
    }),
    tasks: Object.freeze({
      toolFamily,
      createdCount,
      completedCount,
      survivedCompaction: [...createdAt].some(([identifier, creationIndex]) =>
        compactionCycles.some(({ pre, post }) =>
          creationIndex < pre && (observedAt.get(identifier) ?? []).some((index) => index > post))),
    }),
    tools: Object.freeze({
      visibleCountBefore, visibleCountAfter, searchAvailable: searchObserved && searchAvailable, reasonCode,
    }),
    mcp: Object.freeze({
      connectedCount, visibleToolCount,
      beforePercent: mcpBeforePercent,
      afterPercent: mcpAfterPercent,
      deltaPercent: mcpBeforePercent === null || mcpAfterPercent === null
        ? null : mcpAfterPercent - mcpBeforePercent,
    }),
    session: Object.freeze({
      resumeTasksObserved,
      rewindTasksObserved,
      rewindContextObserved,
      rewindAuthorizationInvalidated,
      isolatedClearObserved,
    }),
    window: Object.freeze({
      reportedWindow,
      observedWindow,
      reasonCode: windowReasonCode,
      absoluteOverrideEvidenceGated: windowReasonCode === 'WINDOW_REPORTING_DIVERGENCE' && absoluteOverrideApplied,
    }),
    runtime: Object.freeze(runtime),
  });
}


export function findForbiddenKeys(value, prefix = '') {
  if (!value || typeof value !== 'object') return [];
  const found = [];
  for (const [key, child] of Object.entries(value)) {
    const location = prefix ? `${prefix}.${key}` : key;
    if (FORBIDDEN_KEYS.has(key.toLowerCase())) found.push(location);
    found.push(...findForbiddenKeys(child, location));
  }
  return found;
}


function parseArgs(args) {
  let root;
  let runtimeJsonl;
  for (let index = 0; index < args.length; index += 1) {
    const option = args[index];
    if (option === '--root' && args[index + 1]) root = args[++index];
    else if (option === '--runtime-jsonl' && args[index + 1]) runtimeJsonl = args[++index];
    else throw new Error(`unsupported inventory argument: ${option}`);
  }
  if (!root) throw new Error('--root is required');
  return { root, runtimeJsonl };
}


export async function main({ args = process.argv.slice(2), output = process.stdout, error = process.stderr } = {}) {
  try {
    const options = parseArgs(args);
    const report = { static: await collectStaticInventory(options.root) };
    if (options.runtimeJsonl) {
      const raw = await safeText(path.resolve(options.runtimeJsonl), 'runtime JSONL');
      const events = raw.split(/\r?\n/u).filter(Boolean).map((line) => parseStrictObject(line, 'runtime JSONL event'));
      report.runtime = normalizeRuntimeEvidence(events);
    }
    if (findForbiddenKeys(report).length) throw new Error('forbidden retained inventory key');
    output.write(`${JSON.stringify(report)}\n`);
    return 0;
  } catch {
    error.write('Context inventory failed safely.\n');
    return 1;
  }
}


if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
