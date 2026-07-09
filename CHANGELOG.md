# Changelog

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
