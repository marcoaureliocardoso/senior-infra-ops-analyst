# Security Policy

This skillset is designed for authorized infrastructure operations only.

Do not store secrets, credentials, tokens, private keys, production inventories, customer data, or raw sensitive logs in this repository. Use `.gitignore` patterns and review diffs before commits.

Security-sensitive commands must be classified using `references/risk-levels.md` and documented with scope, minimization, redaction guidance, approval gates, and validation steps.

## Automated scanning

CI runs on every PR and push to main via `.github/workflows/security.yml`:

- **CodeQL** (Python): static analysis for security vulnerabilities
- **ShellCheck**: static analysis for all bash scripts

## Reporting

Report security issues at https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/issues.
