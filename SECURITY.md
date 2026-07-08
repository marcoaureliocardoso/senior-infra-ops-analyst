# Security Policy

This skillset is designed for authorized infrastructure operations only.

Do not store secrets, credentials, tokens, private keys, production inventories, customer data, or raw sensitive logs in this repository. Use `.gitignore` patterns and review diffs before commits.

Security-sensitive commands must be classified using `references/risk-levels.md` and documented with scope, minimization, redaction guidance, approval gates, and validation steps.

Report issues by opening the configured issue tracker after the repository URL is finalized. Until then, maintainers should track security findings in a private channel.
