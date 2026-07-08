# Changelog

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
