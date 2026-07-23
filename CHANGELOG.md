# Changelog

## 0.9.0 - 2026-07-23

- Preloaded all 12 subagents with their documented role-specific primary skills through native Claude Code `skills` frontmatter and allowed the `Skill` tool for on-demand access to the rest of the catalog.
- Extended `validate-content.py` with strict frontmatter parsing to reject missing delimiters and missing, malformed, empty, duplicated, unregistered, or documentation-divergent subagent skill preloads.
- Updated `AGENTS.md`, `README.md`, and `docs.md` to document focused startup preload behavior without pinning Claude Code, Nori, or model versions.

## 0.8.0 - 2026-07-23

- Unified operational risk under the exclusive levels `SAFE_READ_ONLY`, `LOW_RISK_CHANGE`, `DISRUPTIVE_CHANGE`, and `DESTRUCTIVE`; removed the undefined `STATE_CHANGING` and abbreviated `DISRUPTIVE` labels from active instructions.
- Added `EXTERNAL_SIDE_EFFECT` for externally persisted ticket, comment, message, approval, assignment, CMDB, and audit-workflow actions, with exact-target/content confirmation and explicit approval.
- Added deterministic highest-impact classification, modifier composition, and rollback-or-compensating-action rules to the canonical risk reference and command protocol.
- Reclassified ambiguous operations across CI/CD, containers, Kubernetes, databases, PKI, monitoring, network edge, disaster recovery, audit, and ITSM/CMDB references.
- Updated skills, subagents, slash commands, examples, and templates so every AI entry point uses the same risk and approval vocabulary.
- Extended `validate-content.py` to require the canonical levels/modifiers in core policy artifacts and reject deprecated or invented risk-level tokens.

## 0.7.0 - 2026-07-20

- `infrastructure-troubleshooting` v0.5.0: hypothesis discipline (one command, one hypothesis, explicit confirm/refute), multi-layer evidence gathering at component boundaries, anti-thrashing mechanism (3+ refuted hypotheses → re-examine layer/fundamentals). Adapted from `systematic-debugging` for infrastructure domains.
- `root-cause-analysis` v0.5.0: backward tracing (5-step method from symptom to original trigger), trigger vs root cause distinction with concrete trace chain example, defense-in-depth validation at entry boundary and failure layer. Adapted from `root-cause-tracing` for infrastructure domains.
- `read-the-damn-docs` declared as hard dependency in `nori.json` and `AGENTS.md` — forces web-search for current official docs before acting on third-party infrastructure tools (CLIs, APIs, cloud services).
- `.cspell.json` extended with `NXDOMAIN`.

## 0.6.1 - 2026-07-20

- Nori registry packaging metadata: `.nori-version`, `profile.json`, `skills.json`, `docs.md` (comprehensive Noridoc), and 24 `skills/*/nori.json` files for publication readiness.
- Validators extended: `validate-schema.py` checks all packaging metadata files (existence, JSON syntax, required fields, semver, bidirectional `skills.json ↔ nori.json` cross-reference); `validate-content.py` checks `docs.md` Noridoc header.
- `.cspell.json` extended with `Noridoc`, `Cardoso`, `slashcommands`.
- Link validation fix: fictional/placeholder URLs (`.local` domains, bare hostnames, `.example.edu`, `tests/reports/`) filtered from link audit to eliminate permanent false positives.
- CI maintenance: `cspell-action` upgraded to v8, `markdownlint-cli2-action` upgraded to v24 with MD060 (table-column-style) disabled — aligns with AI-first document philosophy where compact tables save tokens.
- `.cspell.json` extended with `datatracker`.

## 0.6.0 - 2026-07-11

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

## 0.5.0 - 2026-07-09

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
- Dependabot updates: `actions/checkout` v4.2.2→v7.0.0, `actions/setup-python` v5.3.0→v6.3.0, `github/codeql-action` v3→v4, `markdownlint-cli2-action` v19→v24, `cspell-action` v6→v8.

## 0.5.1 - 2026-07-09

- Robust link-checking: scans all markdown files (141 URLs), `--json` flag for machine-readable output, GET fallback for servers that reject HEAD (NIST, Microsoft Learn, Netgate docs).
- Historical link health tracking: living issue with trend data (new this week, fixed this week, persistent), state embedded as hidden JSON for run-to-run comparison, auto-close when all links reachable, auto-reopen when broken links return.
- Level 1 deterministic link auto-fix: pattern-based URL correction for known link rot patterns (RFC Editor → datatracker.ietf.org). Suggestions posted in link-audit issue with `sed` one-liner for application.
- 13 RFC links corrected: `rfc-editor.org` URLs replaced with `datatracker.ietf.org/doc/html/rfcNNNN` after context verification confirmed identical RFC specifications.
- Link-audit strategy documented in `ROADMAP.md` with 3-level plan (deterministic → AI-assisted → automated PR) and cost/benefit matrix.
- Scheduled maintenance workflow hardened: inline Python heredoc replaced with `tests/link-audit-issue.py`, placeholder URL filtering, proper `gh` CLI issue management, 90-day artifact retention.
- New labels: `maintenance`, `links`.
- Documentation audit against Nori Skills standards: removed redundant `skill_id` from 10 skills (YAGNI), updated `CONTRIBUTING.md` with validation pipeline and AI-first conventions, updated `SECURITY.md` with automated scanning info.

## 0.4.4 - 2026-07-08

- Added YAML frontmatter with operational descriptions to all 20 slash commands.

## 0.4.3 - 2026-07-08

- Added populated examples for the 7 original core skills.
- Added related-reference sections to all original references and strengthened cross-reference validation.
- Added cloud operations template and operator slash commands for SSH, load balancers, monitoring stacks, web gateways, CI/CD, and ITSM updates.
- Fixed safety gaps: approval gates for automation/capacity operations, `pfctl -d` classification, Kubernetes destructive command examples, and token-in-shell-history warnings.
- Aligned Kubernetes/K3s and network risk modifiers, including `SENSITIVE_OUTPUT` and `RESOURCE_INTENSIVE`.
- Hardened network probe Python fallback with an OS-level timeout when available.
- Expanded project hygiene with additional `.gitignore` security patterns, CI link validation, Makefile clean target, and local pre-commit checks.

## 0.4.2 - 2026-07-08

- Populated 13 previously skeletal roadmap examples with realistic evidence sequences, interpretations, safe next actions, approval gates, and output records.
- Clarified `AGENTS.md` expanded-domain reference heading for v0.4.0/v0.4.1 coverage.
- Updated validation to detect skeletal example files and empty field-only example patterns.

## 0.4.1 - 2026-07-08

- Replaced generic roadmap skill bodies with domain-specific operational requirements.
- Added dedicated Kubernetes operations skill, reference, template, example, and `/k8s-triage` slash command.
- Added examples for all v0.4 roadmap domain skills.
- Removed duplicated root templates and standardized template ownership under `skills/<skill>/templates/`.
- Deepened ITSM/CMDB and disaster recovery drill references.
- Added related-reference sections across domain references.
- Expanded validation for examples, template ownership, Kubernetes coverage, and repeated required-block detection.

## 0.4.0 - 2026-07-08

### Added

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

### Changed

- `ROADMAP.md` now separates completed v0.4.0 coverage from future deep-dive improvements.
- `AGENTS.md` and `nori.json` now reference all new domain references.

## 0.3.4 - 2026-07-08

- Performed live external-link validation via web retrieval because the local container could not resolve external DNS for curl-based checks.
- Replaced direct-fetch-problematic external references with validated canonical or mirror URLs for pfSense packet capture, PowerShell cmdlet references, AD replication troubleshooting, systemd/journalctl/tcpdump manuals, and VMware ESXi troubleshooting.
- Added a live validation report documenting direct passes, alternate confirmations, unavailable local PowerShell parser, and residual caveats.

## 0.3.3 - 2026-07-08

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

## 0.3.2 - 2026-07-08

- Expanded skill-level templates.
- Added script help flags.
- Expanded external references.
- Added PowerShell validation helper.

## 0.3.1 - 2026-07-08

- Fixed Markdown tables and command-modifier consistency.
- Hardened narrow network probe input handling.

## 0.3.0 - 2026-07-08

- Added cloud operations, SLO/SLI observability, RCA artifacts, risk taxonomy, slash commands, templates, and helper scripts.
