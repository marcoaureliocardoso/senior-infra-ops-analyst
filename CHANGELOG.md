# Changelog

Unpublished package states were declared in package metadata but have no Git
tag. Tagged versions correspond to repository tags.

## Unreleased package states

### 0.14.0 (unreleased) - declared 2026-08-25

- Added one global installed authority policy and a canonical untrusted-input reference that treat external content as data, preserve the operator's authority, and prohibit embedded instructions from authorizing actions.
- Applied the same local rule to all 12 independently versioned first-class subagents and advanced their component manifests to `1.1.0` without pinning the runtime, provider, model, or context window.
- Added bounded, sanitized, non-persistent adversarial result records that retain only role, outcome, reason, tool-call count, and canary-exposure count.
- Preserved native authorization and credential semantics: untrusted input cannot grant approval, compacted or unverifiable authorization must be re-established, and the deterministic deny hook cannot inspect tool input.
- Added source, staging, installed-form, parser, safety, and provider-free smoke validation; one separately authorized runtime-specific active-model matrix passed all 13 roles with zero tool-call attempts and zero canary exposures.
- Documented residual model and containment risk, fail-closed boundaries, operator recovery, and the exclusion of P0-04B browser automation beyond interfaces and context impact.

### 0.13.0 (unreleased) - declared 2026-08-21

- Defined one fail-closed native execution-routing matrix for protected main-session Bash, protected executor fallback, typed tools, and no-execution outcomes.
- Added project-local opt-in main-session hooks with exact package ownership, conflict detection, bounded locking, settings-first transactions, crash recovery, idempotent apply, and owned-only rollback.
- Added source and installed-form validation for ephemeral coverage proof without treating exact settings, `bypassPermissions`, or a separate probe as authorization for later commands.
- Added a bounded no-provider PTY self-test for exact nonce-bound main default, main bypass, and genuinely delegated executor fallback denials, with a content-free `SubagentStart` diagnostic and a disposable coordinator whose sole tool is `Agent(diagnostic-operator)`; after an earlier inconclusive run exposed a global
  `--tools Agent` confounder, a separately authorized Bubblewrap-isolated provider run observed all three exact denials and passed the live acceptance gate.

### 0.11.1 (unreleased) - declared 2026-08-08

- Updated every external GitHub Action to its stable release and immutable full commit SHA, including checkout v7.0.1, setup-python v7.0.0, CodeQL v4, upload-artifact v7.0.1, action-gh-release v3.0.2, markdownlint-cli2-action v24.2.0, and cspell-action v8.4.0.
- Migrated CodeQL from v3 to v4 while preserving the exact Python and JavaScript/TypeScript analysis matrix.
- Added exact Python 3.12 and 3.14 schema-validation lanes with direct fail-closed matrix wiring.
- Provisioned ShellCheck 0.11.0 from the official release archive with a fixed SHA-256 verification and an exact pre-analysis version assertion.
- Extended executable workflow mutations for immutable Action references, alternate YAML mappings, Python matrix decoys and expansion, unsafe controls, and ShellCheck supply-chain or ordering drift.
- Changed GitHub Actions Dependabot cadence from monthly to weekly.
- Left Claude Code, Nori Skillsets, DeepSeek, and `model: inherit` unchanged and outside the toolchain upgrade.

### 0.11.0 (unreleased) - declared 2026-07-26

- Added native Claude Code `PreToolUse` and `PostToolUse` hooks to all eight executor subagents, invoking one shared deterministic validator and approval recorder through the Nori-installed skills root.
- Added strict bounded event parsing, separate Bash and PowerShell lexers, full pipeline/redirection graphs, a finite infrastructure command catalogue, explicit target binding, and conservative unknown-mode handling.
- Added mode-aware authorization: normal modes ask for catalogued changes, `bypassPermissions` allows non-destructive catalogued changes, destructive calls always ask, and unknown or unsafe calls deny with operator-visible redacted reasons.
- Added first-use literal approval and bounded non-secret session/domain/identity/transport binding activated only by matching successful `PostToolUse` evidence.
- Added parser-aware model-visible credential handling, provider/helper/reference support, exact direct decryptor-to-consumer flows, redaction before policy output, structural non-secret action identities, and minimal append-only audit metadata.
- Added a fail-closed launcher and process behavior for missing runtime/artifact, internal deadlines, malformed input/output, unexpected stdout, encoding, policy, serialization, and audit failures.
- Hardened the catalogue against verb smuggling, unbounded logs/scans/queries, unsafe filter file operands, arbitrary PowerShell `Get-*`, authenticated HTTP redirect/persistence, SSH proxy-command injection, and unlisted Git/GitHub operations.
- Closed second-review semantic gaps for nested PowerShell expressions, in-command configuration/helper overrides, curl local-file request sources, SSH local execution hooks, Kubernetes raw endpoints, and enabled follow/watch or pagination-disabling forms.
- Closed third-review credential and destination gaps by recognizing every catalogued curl/Redis literal spelling, excluding the non-secret identity marker from transport classification, denying unbound curl route/TLS overrides, and enforcing a closed Kubernetes option schema that rejects endpoint, credential, trust, impersonation, and plugin overrides.
- Closed fourth-review precedence and binding gaps by rejecting repeated curl methods and Kubernetes singleton selectors, detecting curl cookie and Redis compact-quoted credentials, denying unbound AWS/Docker route, trust, diagnostic, and configuration controls, binding named AWS profile assignments, and requiring literal HTTP origins.
- Closed fifth-review binding and raw-token gaps by rejecting mixed literal credential transports, repeated allowlisted assignments and Redis singleton selectors, every Docker `-H` remote-host spelling, and by redacting complete lexer-delimited credential values across concatenated quotes.
- Closed sixth-review Redis trust and scope gaps with a closed CLI option schema, denial of insecure/unbound routing and trust controls, and a canonical approval domain containing transport, host, port, database, and ACL user.
- Closed seventh-review command-semantics gaps with exact Redis verb grammars, destructive classification for non-positive `EXPIRE`, bounded composite `CLIENT KILL`, and mandatory approval for mutable HTTP effects.
- Closed eighth-review gaps with client-specific HTTP option parsers, canonical local output-effect binding and mandatory confirmation, closed PostgreSQL/MySQL selector domains, and destructive parity for every supported Git branch deletion alias.
- Closed ninth-review routing and identity gaps by rejecting HTTP authority overrides and dynamic headers, requiring explicit network database selectors, rejecting tilde output expansion, and treating header-bearing stdout pseudo-sinks as sensitive native-confirmation paths.
- Closed tenth-review domain and disclosure gaps by rejecting PostgreSQL route/trust environment overrides, MySQL socket-selecting host aliases, and curl trace output or persistence whenever a literal credential is present.
- Closed the final adjacent-review gaps by deriving credential reuse from the exact credential-bearing stage and by fully consuming MongoDB, IP batch, remote-transfer, packet-capture, hierarchical `ctr`, Git read-output, and kernel-log control semantics.
- Closed follow-up review gaps by mapping literal spans to their true composition stage, denying multi-stage credential ambiguity, canonicalizing all accepted `scp`/`sftp` endpoint and transport selectors, classifying packet capture `-w -` as sensitive stdout, and rejecting duplicate capture aliases.
- Closed final effective-invocation gaps by requiring the owning catalogued stage to consume the detected literal transport and client-specific variable selector, and by treating `-4`, `-6`, and case-normalized `AddressFamily` as one audited remote-transfer selector.
- Closed final catalogue-prefix gaps with a complete Git push grammar and repository binding, finite journal/container log grammars, bounded verb-specific GitHub CLI reads with mandatory confirmation for broad run logs, and denial of Kubernetes cluster dumps.
- Closed adjacent review gaps by rejecting every executable Git `::` remote-helper transport, requiring explicit GitHub repository domains, preserving container-log targets, and denying the real positional Kubernetes `cluster-info dump` operation for kubectl and k3s.
- Restricted Git push URL repositories to Git's reviewed exact-lowercase native transports so unknown or case-altered `scheme://` values cannot invoke external `git-remote-<scheme>` helpers.
- Required Git push repository operands to be explicit URLs, SCP-like addresses, or local paths; named remotes deny, every parsed push requires native confirmation even in `bypassPermissions`, and audit identifies only the requested address because persistent Git configuration can still rewrite the effective repository or helper.
- Closed RV-89 by denying curl redirect-following flags, requiring PowerShell HTTP clients to set `-MaximumRedirection 0`, and routing literal secret-bearing vendor headers through authorization redaction and approval.
- Closed RV-90 with complete local `git add`, `git commit`, and `git tag` grammars, canonical targets, destructive amend/force/delete classification, and explicit documentation that configured Git hooks, filters, signers, and indirect subprocesses remain outside the current-call enforcement boundary.
- Closed RV-91 by classifying enabled `kubectl` and `k3s kubectl apply --prune` as destructive while preserving explicit false values and denying malformed or repeated prune controls.
- Closed RV-92 by requiring exactly one canonical `-NoProfile` on `pwsh` and `powershell` wrappers before the analyzed payload, with dedicated safe reformulation guidance for missing or duplicate profile suppression.
- Closed RV-93 by adding JavaScript/TypeScript to the CodeQL matrix and executable workflow-mutation tests that require the exact Python plus JavaScript/TypeScript language set.
- Closed RV-94 by requiring exactly one `curl -q` or `curl --disable` control as the first argument so implicit default configuration cannot alter the audited request.
- Closed RV-95 by recognizing Azure Functions and API Management key headers as authorization credentials while preserving benign adjacent header names.
- Closed RV-96 and RV-97 by proving one exact CodeQL matrix drives direct unconditional fail-closed init/analyze steps in the same job, rejecting textual/YAML lookalikes and non-canonical mapping keys, and documenting platform-qualified test totals instead of one ambiguous universal count.
- Added native `PreToolUse` common-field compatibility, including bounded `prompt_id` and documented `effort.level`, plus quoted, escaped, Unicode, empty, and repeated literal-credential handling and direct `gpg`/`age` to `sudo -S` or `sshpass -d 0` flows.
- Added executable fixture-ledger/orphan gates, bounded per-stage findings, four deterministic property seeds, 100% critical line/function/branch coverage including the command catalogue and output resolver, eighty security mutations with pristine baselines and typed matching assertion witnesses, byte-equivalent installed artifacts, and installed-corpus behavior probes.
- Replaced generated coverage labels with executable semantic fixtures for every finite grammar, operator, command-family, reason-code, limit, credential-transport, edge-case, and independent-review inventory item.
- Extended the executable review ledger and direct security regressions with separated, equals-attached, compact, quoted-literal, boolean-false, and boundary variants for every corrected gap.
- Made ordinary successful `PostToolUse` events silent no-ops when no credential binding is pending, and forced process-argument plus all AWS `get-*` reads through native `ask`.
- Hardened the live harness for native executor selection, non-root Debian/WSL usrmerge, minimal read-only DNS/TLS mounts, dynamic loopback ports, and a header/body-free POST fixture. Normal provider credentials remain an explicitly acknowledged temporary exception with provider egress open; isolation and scans reduce but do not eliminate exfiltration risk.
- Added ADR-004 and aligned all model-facing command and credential instructions while keeping Claude Code, Nori, Node.js, and model versions unpinned.

### 0.9.1 (unreleased) - declared 2026-07-23

- Completed a retroactive independent review of P0-01 and resolved all six
  Important findings; no Critical findings were reported.
- Corrected modifier-only and mixed-base classifications across the canonical
  reference, containers, Kubernetes, cloud, network probes, message queues,
  privileged access, audit, vendor escalation, and ITSM/CMDB workflows.
- Made ITSM approval actions inherit the highest plausible impact of the
  execution they authorize instead of hard-coding `LOW_RISK_CHANGE`.
- Added a canonical control matrix covering approval, validation, rollback,
  recovery evidence, and compensating actions for every base level.
- Replaced broad token matching with context-aware risk-expression validation
  across nested Markdown and skill scripts.
- Added twelve mutation-style regression tests for invented levels,
  modifier-only records and prose, multiple base levels, one-line and
  multiline script fields, escaped table pipes, nested scripts, valid
  classifications, and false-positive resistance.
- Kept runtime selection portable without pinning Claude Code, Nori, or model versions.

### 0.9.0 (unreleased) - declared 2026-07-23

- Preloaded all 12 subagents with their documented role-specific primary skills through native Claude Code `skills` frontmatter and allowed the `Skill` tool for on-demand access to the rest of the catalog.
- Extended `validate-content.py` with strict frontmatter parsing to reject missing delimiters and missing, malformed, empty, duplicated, unregistered, or documentation-divergent subagent skill preloads.
- Updated `AGENTS.md`, `README.md`, and `docs.md` to document focused startup preload behavior without pinning Claude Code, Nori, or model versions.

### 0.8.0 (unreleased) - declared 2026-07-23

- Unified operational risk under the exclusive levels `SAFE_READ_ONLY`, `LOW_RISK_CHANGE`, `DISRUPTIVE_CHANGE`, and `DESTRUCTIVE`; removed the undefined `STATE_CHANGING` and abbreviated `DISRUPTIVE` labels from active instructions.
- Added `EXTERNAL_SIDE_EFFECT` for externally persisted ticket, comment, message, approval, assignment, CMDB, and audit-workflow actions, with exact-target/content confirmation and explicit approval.
- Added deterministic highest-impact classification, modifier composition, and rollback-or-compensating-action rules to the canonical risk reference and command protocol.
- Reclassified ambiguous operations across CI/CD, containers, Kubernetes, databases, PKI, monitoring, network edge, disaster recovery, audit, and ITSM/CMDB references.
- Updated skills, subagents, slash commands, examples, and templates so every AI entry point uses the same risk and approval vocabulary.
- Extended `validate-content.py` to require the canonical levels/modifiers in core policy artifacts and reject deprecated or invented risk-level tokens.

## Tagged versions

### 0.12.0 - 2026-08-13

- Added native task-list and Compact Instructions for continuity across long Claude Code sessions.
- Added operator-owned preventive auto-compaction settings with default 72%, preservation of existing 70–75% values, conflict detection, atomic apply, and owned-only rollback.
- Added an opt-in stateless context status line and canonical non-blocking `PreCompact`/`PostCompact` hooks to all 12 subagents.
- Extended the opt-in status line with the exact continuity-preserving `/compact` suggestion when native used context is strictly above the effective 70-75% threshold, while leaving native automatic compaction enabled.
- Invalidated pending and active credential reuse at compaction, including conservative all-binding invalidation when the session identity cannot be proved.
- Added content-free measurement for 25 skills, 12 subagents, MCPs, tool search, context percentages, native task continuity, and provider-window evidence.
- Added deterministic safety, installed-artifact, parser, launcher, and isolated live DeepSeek validation contracts without pinning runtime versions or an absolute context window.
- Added runtime detection for native auto-compaction and a structural-only live hook observer; the real route blocks rather than deriving an automatic absolute fallback.
- Hardened the live PTY driver to wait for delayed `PostCompact` within its bound and reject missing, orphaned, duplicated, or incorrectly ordered manual hook sequences.
- Kept `CLAUDE_CODE_AUTO_COMPACT_WINDOW` outside normal configuration and gated its diagnostic use on observed window-reporting divergence or an exact operator-approved match with the native runtime capacity.
- Added a fail-closed confirmed-window live diagnostic, fixed fresh-session pressure sizing, and made the PTY controller retry partial writes until every bounded prompt byte is delivered.
- Standardized delivered agent and roadmap guidance in English, removing the Portuguese-default response rule.
- Consolidated version history in `CHANGELOG.md` and replaced duplicated README release sections with a canonical link.
- Aligned the canonical Nori manifest, made root `AGENTS.md` mandatory, added reproducible allowlisted staging, and proved isolated Nori installation with operator content preserved outside one managed block.
- Hardened staging replacement with exact inventory identity, unresolved-path link/reparse rejection, atomic move-aside recovery, special-file checks, current-source CI validation, complete installed asset evidence, and fresh verified ZIP creation.
- Prevented archive output from overlapping source or staging and from traversing symlink, junction, or reparse-point paths.
- Promoted all 12 subagents to first-class Nori components with independent `1.0.0` manifests, canonical `SUBAGENT.md` sources, strict cross-reference validation, and verified flattening into Claude Code's installed agent format.
- Left P0-04B browser automation out of scope.

### 0.10.0 - 2026-07-27

- Added role-specific native Claude Code `maxTurns`, exclusive `tools` allowlists, and defense-in-depth `disallowedTools` to all 12 subagents.
- Denied `Write` and `Edit` globally and removed `Bash` from incident coordination, change management, RCA, and security review.
- Added cooperative budgets, tool rationales, safe external-query instructions, and eight-field incomplete-work handoffs.
- Added final runtime-precedence blocks so budget-exhausted handoffs override each agent's normal output.
- Added a canonical runtime-policy validator with mutation coverage for limits, tool drift, duplicates, unknown tools, critical denials, rationales, and handoffs.
- Added semantic comparison of all source and Nori-installed subagents plus manifest validation for root `type: skillset`.
- Added an opt-in OS-sandboxed Claude Code/Nori behavioral smoke harness with exact-command guards, delegated cutoff evidence, and a no-API parser self-test.
- Added indexed ADRs for P0-01, P0-02, and P0-03.
- Kept Claude Code, Nori, and model versions unpinned; `model: inherit` remains mandatory.

### 0.7.0 - 2026-07-20

- `infrastructure-troubleshooting` v0.5.0: hypothesis discipline (one command, one hypothesis, explicit confirm/refute), multi-layer evidence gathering at component boundaries, anti-thrashing mechanism (3+ refuted hypotheses → re-examine layer/fundamentals). Adapted from `systematic-debugging` for infrastructure domains.
- `root-cause-analysis` v0.5.0: backward tracing (5-step method from symptom to original trigger), trigger vs root cause distinction with concrete trace chain example, defense-in-depth validation at entry boundary and failure layer. Adapted from `root-cause-tracing` for infrastructure domains.
- `read-the-damn-docs` declared as hard dependency in `nori.json` and `AGENTS.md` — forces web-search for current official docs before acting on third-party infrastructure tools (CLIs, APIs, cloud services).
- `.cspell.json` extended with `NXDOMAIN`.

### 0.6.1 - 2026-07-20

- Nori registry packaging metadata: `.nori-version`, `profile.json`, `skills.json`, `docs.md` (comprehensive Noridoc), and 24 `skills/*/nori.json` files for publication readiness.
- Validators extended: `validate-schema.py` checks all packaging metadata files (existence, JSON syntax, required fields, semver, bidirectional `skills.json ↔ nori.json` cross-reference); `validate-content.py` checks `docs.md` Noridoc header.
- `.cspell.json` extended with `Noridoc`, `Cardoso`, `slashcommands`.
- Link validation fix: fictional/placeholder URLs (`.local` domains, bare hostnames, `.example.edu`, `tests/reports/`) filtered from link audit to eliminate permanent false positives.
- CI maintenance: `cspell-action` upgraded to v8, `markdownlint-cli2-action` upgraded to v24 with MD060 (table-column-style) disabled — aligns with AI-first document philosophy where compact tables save tokens.
- `.cspell.json` extended with `datatracker`.

### 0.6.0 - 2026-07-11

- 12 role-focused subagents added under `subagents/` aligned with the official Nori skillset format.
- Subagents: `incident-commander`, `diagnostic-operator`, `change-manager`, `rca-facilitator`, `observability-sre`, `security-operations-reviewer`, `cloud-platform-operator`, `kubernetes-operator`, `database-operator`, `network-edge-operator`, `release-cicd-operator`, `audit-evidence-collector`.
- Each subagent includes YAML frontmatter (`name`, `description`, `tools`, `model: inherit`), required references, primary skills, operating boundaries with `<required>` blocks, domain-specific procedures, decision rules, and output specifications (100-150 lines each).
- `nori.json` extended with `"subagents"` array registering all 12 subagents by `id`, `name`, and `description`.
- 20 slash commands mapped to subagents via `allowed-tools: Task(subagent_type:<name>)` in YAML frontmatter. `diagnostic-operator` serves as catch-all for domains without dedicated subagents (PKI, SSH, containers, message queues, DR, vendor escalation, ITSM, runbooks).
- Validation extended in `tests/validate-schema.py`: subagent array presence, required fields per entry (`id`, `name`, `description`), uniqueness enforcement, disk-to-manifest file registration check.
- Validation extended in `tests/validate-content.py`: frontmatter field completeness, `<required>` block presence, `risk-levels.md` safety model reference, internal cross-reference integrity, 60-line minimum anti-stub threshold, tool-set whitelist validation, `model: inherit` enforcement, and `allowed-tools` cross-validation between slash commands and registered subagents.
- `AGENTS.md` updated with subagents delegation table for agent discoverability.
- `README.md` updated with subagents summary table and tool assignments.
- `.cspell.json` extended with 20 domain-specific terms for spell-check coverage of subagent content.
- `.claude/` added to `.gitignore`.

### 0.5.1 - 2026-07-09

- Robust link-checking: scans all markdown files (141 URLs), `--json` flag for machine-readable output, GET fallback for servers that reject HEAD (NIST, Microsoft Learn, Netgate docs).
- Historical link health tracking: living issue with trend data (new this week, fixed this week, persistent), state embedded as hidden JSON for run-to-run comparison, auto-close when all links reachable, auto-reopen when broken links return.
- Level 1 deterministic link auto-fix: pattern-based URL correction for known link rot patterns (RFC Editor → datatracker.ietf.org). Suggestions posted in link-audit issue with `sed` one-liner for application.
- 13 RFC links corrected: `rfc-editor.org` URLs replaced with `datatracker.ietf.org/doc/html/rfcNNNN` after context verification confirmed identical RFC specifications.
- Link-audit strategy documented in `ROADMAP.md` with 3-level plan (deterministic → AI-assisted → automated PR) and cost/benefit matrix.
- Scheduled maintenance workflow hardened: inline Python heredoc replaced with `tests/link-audit-issue.py`, placeholder URL filtering, proper `gh` CLI issue management, 90-day artifact retention.
- New labels: `maintenance`, `links`.
- Documentation audit against Nori Skills standards: removed redundant `skill_id` from 10 skills (YAGNI), updated `CONTRIBUTING.md` with validation pipeline and AI-first conventions, updated `SECURITY.md` with automated scanning info.

### 0.5.0 - 2026-07-09

- Complete CI critical revision — replaced single monolithic workflow with 4 hardened, modular workflows.
- New `ci.yml`: 6 parallel jobs (package-validate, lint-hygiene, markdown-lint, spell-check, link-check, nori-schema) with permissions blocks, concurrency groups, pinned runner, hash-pinned actions, and timeouts.
- New `release.yml`: tag-triggered release with version consistency check between git tag and `nori.json`.
- New `security.yml`: CodeQL (Python) + ShellCheck on all bash scripts, weekly schedule.
- New `scheduled-maintenance.yml`: weekly link audit with auto-issue creation and monthly full validation.
- New validators: `tests/validate-schema.py` (nori.json structural integrity), `tests/validate-ci-workflows.sh` (CI quality enforcement).
- Markdownlint tuned for AI-first document conventions — rules that conflict with LLM token efficiency disabled, 48 genuine violations fixed across 35 files, rationale documented in `AGENTS.md`.
- Bug fixes: `set -uo pipefail` → `set -euo pipefail` in link validator, git tracked permissions on bash scripts (100644 → 100755), TBD placeholders replaced with real GitHub URLs, link validation rate-limiting and 429 retry.
- Configuration: `.markdownlint.json`, `.cspell.json`, `.github/dependabot.yml` (github-actions + pip monthly), `.github/link-audit-issue-template.md`.
- CI/Security/Release status badges added to `README.md`.
- Dependabot updates: `actions/checkout` v4.2.2→v7.0.0, `markdownlint-cli2-action` v19→v24, and `cspell-action` v6→v8.

### 0.4.4 - 2026-07-08

- Added YAML frontmatter with operational descriptions to all 20 slash commands.

### 0.4.3 - 2026-07-08

- Added populated examples for the 7 original core skills.
- Added related-reference sections to all original references and strengthened cross-reference validation.
- Added cloud operations template and operator slash commands for SSH, load balancers, monitoring stacks, web gateways, CI/CD, and ITSM updates.
- Fixed safety gaps: approval gates for automation/capacity operations, `pfctl -d` classification, Kubernetes destructive command examples, and token-in-shell-history warnings.
- Aligned Kubernetes/K3s and network risk modifiers, including `SENSITIVE_OUTPUT` and `RESOURCE_INTENSIVE`.
- Hardened network probe Python fallback with an OS-level timeout when available.
- Expanded project hygiene with additional `.gitignore` security patterns, CI link validation, Makefile clean target, and local pre-commit checks.

### 0.4.2 - 2026-07-08

- Populated 13 previously skeletal roadmap examples with realistic evidence sequences, interpretations, safe next actions, approval gates, and output records.
- Clarified `AGENTS.md` expanded-domain reference heading for v0.4.0/v0.4.1 coverage.
- Updated validation to detect skeletal example files and empty field-only example patterns.

### 0.4.1 - 2026-07-08

- Replaced generic roadmap skill bodies with domain-specific operational requirements.
- Added dedicated Kubernetes operations skill, reference, template, example, and `/k8s-triage` slash command.
- Added examples for all v0.4 roadmap domain skills.
- Removed duplicated root templates and standardized template ownership under `skills/<skill>/templates/`.
- Deepened ITSM/CMDB and disaster recovery drill references.
- Added related-reference sections across domain references.
- Expanded validation for examples, template ownership, Kubernetes coverage, and repeated required-block detection.

### 0.4.0 - 2026-07-08

#### Added

- Dedicated skills, references, and templates for all previous ROADMAP domains:
  - database operations
  - container runtime operations beyond Kubernetes control-plane checks
  - load balancers and reverse proxies
  - PKI and certificate lifecycle operations
  - CI/CD operations
  - monitoring stack operations
  - message queues
  - web servers and application gateways
  - SSH and privileged access management
  - ITSM/CMDB workflows
  - disaster recovery drills
  - vendor escalation management
  - audit and compliance evidence collection
- New slash commands: `/db-triage`, `/container-runtime-triage`, `/cert-check`, `/queue-triage`, `/dr-drill`, `/audit-evidence`, `/vendor-escalate`.
- Root templates for database incident, certificate renewal, DR drill, vendor escalation, and audit evidence records.

#### Changed

- `ROADMAP.md` now separates completed v0.4.0 coverage from future deep-dive improvements.
- `AGENTS.md` and `nori.json` now reference all new domain references.

### 0.3.4 - 2026-07-08

- Performed live external-link validation via web retrieval because the local container could not resolve external DNS for curl-based checks.
- Replaced direct-fetch-problematic external references with validated canonical or mirror URLs for pfSense packet capture, PowerShell cmdlet references, AD replication troubleshooting, systemd/journalctl/tcpdump manuals, and VMware ESXi troubleshooting.
- Added a live validation report documenting direct passes, alternate confirmations, unavailable local PowerShell parser, and residual caveats.
- Added project hygiene: `.gitignore`, `.gitattributes`, `Makefile`, pre-commit config, GitHub Actions validation, `CONTRIBUTING.md`, `SECURITY.md`, and this changelog.
- Added a canonical diagnostic order reference and aligned troubleshooting/incident wording to avoid competing diagnostic sequences.
- Added incident severity definitions and clarified that mitigation urgency does not override approval gates.
- Expanded root templates into guided artifacts and aligned `templates/change-plan.md` with the change-management skill.
- Required shared risk vocabulary across all skills.
- Added safety sections to DNS/DHCP, network, cloud, Linux, Windows, and related references.
- Improved cloud operations parity across AWS, Azure, and GCP, including provider-native active probes and example command records.
- Hardened helper scripts: Linux script now degrades on non-root/non-systemd hosts; network script avoids ambiguous `/dev/tcp` fallback when better tools are unavailable.
- Expanded validation from syntax-only checks to manifest integrity, required references, template substance, slash-command template references, risk vocabulary references, and optional link checks.
- Added skill metadata fields: version, last_updated, maintainer, and triggers.

### 0.3.2 - 2026-07-08

- Expanded skill-level templates.
- Added script help flags.
- Expanded external references.
- Added PowerShell validation helper.

### 0.3.1 - 2026-07-08

- Fixed Markdown tables and command-modifier consistency.
- Hardened narrow network probe input handling.
- Added cloud operations, SLO/SLI observability, RCA artifacts, risk taxonomy, slash commands, templates, and helper scripts.

### 0.2.1 - 2026-07-08

- Established the original nine-skill infrastructure operations package for
  diagnostics, incidents, change management, RCA, observability, automation
  safety, runbooks, and capacity and risk review.
- Registered the initial Linux, Windows Server, network, pfSense, DNS/DHCP,
  Active Directory, VMware, Kubernetes/K3s, storage/backup, command-execution,
  risk, and interpretation references.
