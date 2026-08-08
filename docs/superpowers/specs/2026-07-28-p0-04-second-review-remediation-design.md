# P0-04 Second Review Remediation Design
**Status:** Approved by the operator through the instruction to correct every
finding from the current PR #25 review.

**Scope:** Close the six reproducible authorization gaps found on PR #25 head
`9980054` without weakening the approved `bypassPermissions` model. Catalogued,
statically understood operations retain mode-aware autonomy. Dynamic execution,
unmodelled local sources, sensitive raw endpoints, and unbounded streams fail
closed in every mode.

## Considered approaches
1. **Bounded Node.js grammar with per-client allowlists — selected.** It keeps
   the existing standard-runtime dependency, is deterministic before tool use,
   and can reject syntax whose effective behavior is not statically provable.
2. **Invoke a native PowerShell AST parser.** This would model PowerShell more
   completely, but adds a platform/runtime dependency to the hook and creates a
   new availability failure path.
3. **Deny PowerShell, SSH options, HTTP bodies, and Kubernetes reads broadly.**
   This is simple but would remove routine operational capability that remains
   safe when expressed in a bounded literal form.

## Authorization changes
### PowerShell
The lexer rejects unquoted expression delimiters and call/type syntax capable
of evaluating nested commands or methods. Parentheses inside quoted literal
arguments remain data. A read cmdlet is authorized only when the complete
payload remains inside this literal grammar.

### Environment prefixes
The generic assignment prefix accepts only credential literals and the named
AWS profile reference already covered by credential handling. Variables that
select configuration, agents, helpers, loaders, plugins, or executable search
paths are not catalogued. In particular, `GIT_ASKPASS`, `KUBECONFIG`,
`AZURE_CONFIG_DIR`, `CLOUDSDK_CONFIG`, and `SSH_AUTH_SOCK` fail closed. An
operator may configure these outside the model-generated command before Claude
Code starts; the guard does not authorize an in-command override it cannot
inspect.

### HTTP file sources
The curl parser consumes both separated and attached option values. Any option
whose value causes curl to read a local file for a request body, form, JSON, or
upload is denied, including long `--option=value` and compact short-option
forms. Literal bodies remain catalogued. Local response sinks keep their
existing `FILE_WRITE` classification.

### SSH options
SSH client options move from an execution-option denylist to a closed allowlist
of literal transport options. Configuration files and options that can execute
helpers, load providers, alter command execution, or delegate configuration are
not catalogued. The remote payload remains a single literal catalogued stage.

### Kubernetes endpoints and bounds
`kubectl --raw` is denied because the raw URI bypasses resource-aware sensitive
output classification. `logs --follow`, `get --watch`, `get --watch-only`, and
pagination-disabling forms fail closed. Finite log tails and ordinary scoped
get/describe operations remain available; explicit secret/configmap operands
continue to require `ask` in every mode.

## Test architecture
Each reproduced command receives a stable fixture ID in the executable review
ledger and a behavior assertion in the security regression suite. Edge cases
cover separated, equals-attached, and compact short HTTP values; quoted versus
unquoted PowerShell parentheses; SSH split and attached `-o` forms; and every
Kubernetes streaming/raw variant. Tests must be observed failing before the
production change, then passing afterward. The full package gate remains the
final regression check.

## Documentation and review state
ADR-004 and the changelog record the tightened boundary. The independent review
record and its index must no longer authorize merge until these regressions are
fixed and a fresh independent review of the new head records no blocker. The
package remains version `0.11.0`; these corrections are part of the unreleased
P0-04 feature rather than a new release boundary.
