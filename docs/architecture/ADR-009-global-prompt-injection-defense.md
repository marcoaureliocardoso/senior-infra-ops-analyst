# ADR-009 — Global prompt-injection defense

- **Status:** Accepted
- **Date:** 2026-08-25
- **Scope:** Authority, containment, effect boundaries, and validation for untrusted content

## Context

Operational evidence arrives through logs, tickets, documents, source code,
tool and MCP results, websites, and subagent handoffs. Those channels can carry
direct, indirect, encoded, hidden, or role-impersonating instructions. They can
also contain credential-looking values. Treating any such content as authority
could change the objective, disclose protected data, weaken policy, impersonate
an operator, bypass an approval gate, or trigger a tool effect.

Prompt injection is not a solved model property. Instruction text can reduce
the probability of unsafe behavior, but it cannot provide a deterministic
authorization or containment boundary. The package therefore needs overlapping
controls whose strongest guarantees do not depend on hidden model reasoning.

## Decision

Adopt `references/untrusted-input-handling.md` as the canonical global
contract. External and observed content is data, not instructions. It can
support diagnosis, but it cannot establish identity, grant approval, authorize
credential use, change governing policy, delegate work, or trigger an external
effect. Useful facts extracted from a contaminated source are independently
validated before they influence an operational decision.

The contract is inherited from the Nori-installed root instructions and is
reinforced locally in every packaged subagent. Existing native authorization,
risk, credential, and execution controls remain authoritative. Detection
produces a bounded, non-persistent record; it never turns the hostile content
into a new action.

## Authority model

**Authority and provenance** are evaluated separately from content. Governing
platform instructions, the operator's direct request, versioned package policy,
and fresh native authorization evidence can carry authority within their exact
scope. Logs, tickets, documents, web pages, tool output, MCP output, code,
quoted text, and another agent's handoff do not gain authority by sounding
urgent or privileged.

Credentials are authentication material, not instructions or authorization.
A credential-looking value found in evidence cannot be used, forwarded,
persisted, or treated as operator approval. Direct operator disclosure does not
erase the command guard, scope, risk classification, native prompt, or
same-session proof requirements.

## Enforcement layers

1. `AGENTS.md` establishes the required global authority and handling policy.
2. All 12 `SUBAGENT.md` definitions repeat a concise local rule and reference
   the canonical contract exactly once.
3. Source and isolated Nori-install validators fail on missing global markers,
   missing roles, stale definitions, unexpected roles, linked artifacts, or
   unsafe installed layouts.
4. The existing command guard and native execution boundary govern effects.
   A model statement cannot create an `allow`, `ask`, approval, credential
   binding, or current-session runtime proof.
5. The active-model harness adds a disposable deny-all `PreToolUse` hook for
   every tool name. Any proposed tool call fails the adversarial role result,
   even though the hook prevents execution.
6. Bounded JSONL evaluation rejects oversized, deep, malformed, duplicated-key,
   canary-bearing, incomplete, contradictory, or multi-record evidence.

These layers complement Claude Code's native permission system. They do not
replace it, weaken it, or use `bypassPermissions` in the P0-06 live matrix.

## Sanitized records

Each detected attempt uses `PROMPT_INJECTION_ATTEMPT` with exactly five bounded
semantic fields: source type, non-secret source reference, requested effect,
disposition, and `secret_exposure=none`. The record omits the raw payload,
prompt, transcript, compact summary, model output, tool input, token,
credential, configuration value, full contaminated document, canary, and
secret-derived hash.

Automatic persistence is prohibited. The default record exists only in the
current operator response or a structured handoff. A file, ticket, message,
incident record, or other external write remains an independently authorized
`EXTERNAL_SIDE_EFFECT`.

## Validation evidence

Deterministic source-policy tests cover the global contract and all 12 role
definitions. Isolated installation tests prove that Nori emits the required
managed `CLAUDE.md` and exact flattened agents while preserving unrelated
operator content. Bounded parser tests cover the exact role inventory, prompt
generation, record semantics, tool attempts, canary exposure, raw-content
exclusion, size, line, depth, UTF-8, duplicate-key, and aggregation failures.

The deny-all hook tests prove a 64 KiB input bound, duplicate-key rejection,
owner-only content-free audit records, safe symlink failure, and a native
`PreToolUse` deny response. The hook parses the bounded native JSON envelope;
its response and audit depend only on event name and tool name, and it never
logs, emits, or persists `tool_input` values. The live harness self-test covers
passing, tool-call, canary, malformed, and incomplete fixtures without locating
credentials or making a provider request.

Active-model validation is a separate acceptance gate. It requires exact
operator authorization for one main-session probe and one probe for each of the
12 packaged roles, disposable Nori installation, Bubblewrap isolation,
allowlisted provider settings, 120 seconds per role, 1,800 seconds total, no
retry, immediate raw deletion, and exactly 13 passing structural results. Until
that matrix runs successfully, P0-06 remains unaccepted even though this
architectural decision and deterministic implementation are versioned.

## Alternatives rejected

- Instruction-only defense: probabilistic model compliance cannot authorize or
  contain operational effects.
- A semantic firewall or model proxy as the primary gate: it adds a second
  probabilistic interpreter, provider coupling, content retention pressure,
  and bypass paths without replacing native effect controls.
- Treating tool, MCP, browser, or subagent output as delegated authority: those
  channels carry data from independently mutable trust domains.
- Treating credentials as implicit approval: authentication and authorization
  are different decisions.
- Persisting raw detections for later analysis: this expands the secret and
  adversarial-content blast radius.
- Claiming success from a self-test or one runtime: deterministic fixtures do
  not prove model behavior, and one provider run does not prove immunity.

## Consequences and residual risks

The package gains a consistent authority rule across main and delegated work,
deterministic installation drift detection, native effect containment, and
content-free adversarial evidence. It also deliberately refuses some ambiguous
automation and requires fresh operator decisions where provenance or native
proof cannot be established.

Residual risks remain. The configured provider sees the synthetic live prompt,
and normal operational sessions still expose user-supplied conversation content
to their configured model/provider. A same-principal local actor can tamper with
runtime files outside the guarantees of these package checks. Model behavior,
Claude Code capabilities, Nori rendering, providers, MCP servers, skills, and
subagent runtimes can change. A passing matrix is runtime-specific evidence,
not immunity from prompt injection or future regressions.

## Follow-ups

P0-04B remains responsible for browser automation, browser-specific isolation,
and its context impact. It must consume this authority model but requires its
own controls and adversarial validation. Future MCP or tool-search expansion
must preserve provenance labels, least privilege, native authorization, and
the same non-persistence constraints.
