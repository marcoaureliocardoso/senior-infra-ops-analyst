# P0-04 Native Command Guard Design

**Status:** Approved
**Date:** 2026-07-25
**Scope:** P0-04 — apply native `PreToolUse` enforcement to executor subagents

## Context

The project is an AI-first operational skillset executed by Claude Code,
distributed by Nori, and interpreted by the operator-selected model. Its
executor subagents must remain capable of performing real infrastructure
operations. Safety therefore cannot be implemented by removing shell
execution or by relying on the model to classify its own command correctly.

P0-03 limited `Bash` to eight executor roles. P0-04 adds deterministic
command-level enforcement at that remaining capability boundary. Runtime,
installer, and model identifiers are observed during validation and are not
package requirements.

The design was approved with two explicit product requirements:

1. `bypassPermissions`, including sessions started with
   `--dangerously-skip-permissions`, represents deliberate operator selection
   of autonomous execution.
2. Operational authentication must support SSH/sudo passwords, database
   credentials, HTTP/API tokens, PowerShell credentials, cloud and Kubernetes
   identities, credential helpers, and generic secret-bearing environment
   variables.

## Goals

- Keep the eight executor agents operational rather than diagnostic-only.
- Use Claude Code's native `PreToolUse` decision contract.
- Apply a deterministic shared validator to every executor `Bash` call.
- Respect the effective Claude Code permission mode.
- Allow recognized operational changes in autonomous mode.
- Require an exact native decision in non-autonomous mode.
- Fail closed when a command cannot be analyzed conclusively.
- Support legitimate credential use while preventing additional disclosure.
- Preserve the hook and validator path after Nori installation.
- Record hook decisions independently from the model's justification.

## Non-goals

- Do not pin Claude Code, Nori, Node.js, or a model identifier.
- Do not parse DeepSeek APIs or model reasoning content.
- Do not create a daemon, model proxy, approval service, or parallel runtime.
- Do not make Nori a credential vault.
- Do not claim that inline credentials are confidential from the model
  provider or the Claude Code transcript.
- Do not authorize arbitrary, encoded, or semantically ambiguous shell.
- Do not replace later typed MCP interfaces for operations that benefit from
  stronger schemas, idempotency, or transaction semantics.

## Native installation architecture

The following executor agents receive the hook:

- `diagnostic-operator`;
- `observability-sre`;
- `cloud-platform-operator`;
- `kubernetes-operator`;
- `database-operator`;
- `network-edge-operator`;
- `release-cicd-operator`;
- `audit-evidence-collector`.

Each source agent declares a `PreToolUse` hook in native Claude Code
frontmatter with matcher `Bash`. Nori installs Claude Code agents as Markdown
and substitutes `{{skills_dir}}` with the installed skills directory. The hook
uses exec form to invoke the shared validator by absolute installed path:

```yaml
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: node
          args:
            - "{{skills_dir}}/command-driven-operations/scripts/validate-ops-command.mjs"
          timeout: 5
```

Node.js is used because it is already part of the Claude Code/Nori execution
pair. No separately managed Python runtime is introduced.

Source validation checks the exact hook semantics for all eight executors and
the absence of this `Bash` hook from the four analytical roles. Installed
validation compares the source and Nori-produced hook structure and confirms
that the validator path resolves to the installed shared script.

## Input and output contract

The validator reads one JSON event from stdin and requires:

- `hook_event_name` exactly `PreToolUse`;
- `tool_name` exactly `Bash`;
- `agent_type` in the executor allowlist;
- `permission_mode` in the currently documented Claude Code mode set;
- `tool_input.command` as a non-empty bounded string;
- optional `tool_input.timeout` within policy;
- `tool_input.run_in_background` absent or `false`.

It returns only the current structured Claude Code contract:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|ask|deny",
    "permissionDecisionReason": "redacted deterministic reason"
  }
}
```

Malformed input, unknown schema, internal exceptions, audit failure when audit
is required, and unsupported policy states exit with code `2`. No allow
decision is emitted on an error path.

## Permission-mode-aware policy

`permission_mode` is the authoritative effective mode. The validator does not
attempt to distinguish whether `bypassPermissions` originated from
`--dangerously-skip-permissions`, `--permission-mode bypassPermissions`,
settings, or an in-session mode change.

| Command classification | Normal modes | `bypassPermissions` |
|---|---|---|
| Narrow `SAFE_READ_ONLY` | `allow` | `allow` |
| Bounded read with approval modifier | `ask` | `allow` |
| Catalogued `LOW_RISK_CHANGE` | `ask` | `allow` |
| Catalogued `DISRUPTIVE_CHANGE` | `ask` | `allow` |
| Catalogued `DESTRUCTIVE` | `ask` | `ask` |
| Ambiguous, encoded, evasive, or unmodelled | `deny` | `deny` |
| Suspected credential exfiltration | `deny` | `deny` |

Normal modes are `default`, `plan`, `acceptEdits`, `auto`, and `dontAsk`.
Claude Code remains responsible for the final behavior of an `ask` decision
in modes or non-interactive surfaces where a prompt cannot be completed.

`bypassPermissions` is session-level authorization for catalogued
non-destructive operations. It is not a new risk level and does not suppress
deterministic validation. Every call is parsed again and receives its own
redacted audit decision.

`DESTRUCTIVE` retains an exact just-in-time human decision in every mode. This
is the non-negotiable recovery boundary.

## Deterministic command analysis

The validator never executes the proposed command and never asks an LLM to
classify it. It performs bounded lexical analysis and command-family policy
matching.

The initial grammar accepts one foreground command with a deterministically
tokenizable argument vector. A family policy declares:

- executable aliases;
- allowed operational verbs;
- risk level and modifiers;
- required target and environment selectors;
- bounded flags for time, output, namespace, quantity, and fan-out;
- credential-bearing argument positions;
- forbidden options and destructive variants.

Initial coverage prioritizes commands already documented by the project,
including local diagnostics and controlled families for system services,
Kubernetes, containers, cloud providers, databases, networking, SSH, sudo,
PowerShell, Git/CI, and authenticated HTTP operations.

Pipelines, redirections, command substitution, background execution,
interpreter wrappers, remote nested commands, and command chaining are denied
unless a family-specific parser proves every component and data flow safe.
Broad substring or regex matches cannot authorize a command.

Unknown commands remain denied in both modes. The catalog grows through
versioned policy changes and positive plus adversarial tests.

## Target, environment, and scope

Mutating and remote command families must expose target and environment in
arguments that the parser can bind. Examples include Kubernetes context and
namespace, cloud account/profile and region/project/subscription, resource
identifier, remote host, database endpoint, service unit, or explicit API
origin.

Implicit current contexts are acceptable only for command families whose
policy classifies the operation as narrow read-only. A state change with an
implicit or variable-derived target is denied.

An exact native approval applies only to that tool call. Changing an argument,
target, environment, scope, credential transport, timeout, or background flag
causes a new evaluation. In autonomous mode, the new call can still be allowed
only if it independently satisfies the policy.

## Credential handling

Credential use is supported; credential disclosure is minimized.

Supported mechanisms include:

- SSH agent, askpass, `sshpass`, and explicit SSH authentication options;
- sudo timestamp, askpass, and `sudo -S`;
- database environment variables, flags, connection strings, and protected
  credential files;
- HTTP Basic, Bearer, cookie, client-certificate, and header authentication;
- PowerShell `PSCredential`, `ConvertTo-SecureString`, `-Credential`, and
  authenticated headers;
- cloud profiles, SSO, cached sessions, credential helpers, kubeconfig, and
  exec credential plugins;
- generic variables whose names indicate password, token, secret, key, or
  credential content.

Credential references and provider-managed authentication do not change the
operational risk decision.

A detected literal credential raises a normal-mode decision to at least
`ask`, with a redacted warning that the value may already be present in the
model/provider and Claude Code transcript. In `bypassPermissions`, a literal
credential does not by itself prevent an otherwise allowed narrow read,
low-risk change, or disruptive change. Destructive actions still ask.

The validator denies:

- deliberate printing or logging of a secret;
- transfer of a secret to an unrelated process or ambiguous destination;
- authenticated redirects to an unvalidated origin;
- destinations built by substitution, encoded content, or unsupported shell
  composition;
- credential-bearing background jobs;
- secret material used by an unrecognised command family.

The validator must not echo, persist, hash, or include the raw secret in its
decision. Redaction happens before normalization and fingerprinting.

The project recommends provider profiles, credential helpers, agents,
keychains, preloaded environment variables, and direct operator login. These
are recommendations, not mandatory blockers.

## Audit model

Hook decisions are distinct from model reasoning. Audit records contain only
the minimum redacted fields needed to explain enforcement:

- timestamp and session identifier;
- agent type and permission mode;
- risk level and modifiers;
- policy family and deterministic rule identifier;
- parsed target, environment, and scope when non-sensitive;
- credential type and transport, never the credential value;
- normalized redacted-command fingerprint;
- `allow`, `ask`, or `deny`;
- redacted reason code.

Raw commands, transcripts, tool output, credentials, cookies, authorization
headers, connection strings, private keys, and unnecessary personal data are
not written by the guard.

## Validation strategy

### Contract and policy tests

Tests first establish failing cases for:

- malformed and oversized JSON;
- missing or unexpected event, tool, agent, mode, or command fields;
- background commands and invalid timeouts;
- normal versus `bypassPermissions` decisions for every risk level;
- exact target and environment requirements;
- source-to-installed hook preservation;
- fail-closed exception and audit paths.

### Shell and evasion tests

Adversarial fixtures cover:

- pipes and redirections;
- `&&`, `||`, `;`, newlines, and background jobs;
- `$()`, backticks, process substitution, and nested interpreters;
- environment expansion and assignment;
- shell, PowerShell, Python, Node.js, SSH, and sudo wrappers;
- base64, hex, escaped Unicode, control characters, and quoting variations;
- path traversal, symlink-sensitive paths, wildcards, and glob expansion;
- downloads, remote scripts, and authenticated redirects;
- fan-out, broad logs, packet capture, and resource-intensive queries.

### Credential tests

Synthetic markers cover every supported credential transport:

- SSH and sudo passwords;
- database flags, URIs, environment variables, and files;
- HTTP Basic/Bearer/cookie/client-certificate inputs;
- PowerShell credentials;
- cloud, Kubernetes, and Git credential helpers;
- generic token, password, key, and secret variables.

Tests assert that normal mode asks, autonomous mode follows the operation's
policy, destructive actions still ask, exfiltration denies, and no synthetic
secret appears in stdout, stderr, audit output, or retained test artifacts.

### Installed and live behavior

An isolated Nori activation verifies all eight installed executor hooks and
the resolved shared script. The opt-in Claude Code smoke runs only against
synthetic or disposable targets and includes:

- a normal-mode read and controlled mutation;
- a `bypassPermissions` read and controlled mutation;
- a destructive command that still asks or is safely prevented from reaching
  a real executor;
- a malformed-command denial;
- a hook-failure denial;
- a synthetic credential flow with retained artifacts scanned for leakage.

The harness discovers runtime commands and records observed versions without
converting them into compatibility gates.

## Documentation and release impact

Implementation adds ADR-004 and updates the architecture index, README,
project documentation, command-execution policy, risk authorization wording,
release notes, and consistent version metadata. The external TODO is aligned
before implementation and receives final evidence after integration.

P0-05 is narrowed to define when native guarded shell is sufficient and when
typed MCP operations provide materially stronger semantics. It no longer
prohibits every autonomous state change through Bash.

## Capability evidence

The design relies on public native contracts rather than observed version
strings:

- Claude Code hooks reference:
  <https://code.claude.com/docs/en/hooks>;
- Claude Code permission modes:
  <https://code.claude.com/docs/en/permission-modes>;
- Nori Claude Code subagent installation at the observed reference:
  <https://github.com/tilework-tech/nori-skillsets/blob/skillsets-v0.31.0/src/cli/features/shared/subagentsLoader.ts>;
- Nori installed-path substitution at the observed reference:
  <https://github.com/tilework-tech/nori-skillsets/blob/skillsets-v0.31.0/src/cli/features/template.ts>.

The Nori links document the capability evidence available during design. They
are not compatibility pins; installed-artifact tests remain the forward
compatibility contract.

## Residual risks

- A credential pasted into a prompt has already reached the model/provider
  boundary before `PreToolUse`; the hook can only prevent additional
  disclosure.
- Command-family policy cannot cover every current or future infrastructure
  CLI immediately. Unknown commands fail closed until reviewed.
- A parser can establish syntactic target and scope but cannot prove the
  operator's real-world intent.
- `bypassPermissions` is deliberately broad session authorization. It
  increases operational autonomy and blast-radius risk by design.
- The main Claude Code session is outside an executor-scoped hook if it can
  invoke `Bash` directly. Global enforcement remains a separate control unless
  the Nori-installed artifact exposes a supported global hook path.
- Later typed MCP tools remain preferable for complex destructive,
  transactional, multi-target, or externally persisted operations.
