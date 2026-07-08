# Validation Notes

## Local validation

This package includes `tests/validate-package.sh`. It validates JSON and Bash syntax in Unix-like environments.

```bash
./tests/validate-package.sh
```

## PowerShell validation

The PowerShell helper is intended to be parsed with PowerShell itself. Run this on a Windows host or any host with PowerShell 7+:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./tests/validate-powershell-syntax.ps1
```

If PowerShell is not installed, do not claim the `.ps1` file was syntactically validated. Mark it as text-reviewed only.

## Operational validation

Syntax validation does not prove operational safety. Before using helper scripts in production:

- inspect the script content,
- confirm authorization,
- confirm risk classification and modifiers,
- run first in a test or narrow-scoped environment,
- redact sensitive output before sharing.
