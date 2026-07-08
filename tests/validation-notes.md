# Validation Notes

`tests/validate-package.sh` performs local checks that do not require internet access:

- JSON syntax
- manifest-to-disk skill/reference integrity
- `AGENTS.md` required reference alignment
- shared risk-level reference usage across skills
- required skill metadata fields
- non-skeletal templates
- slash command template references
- safety sections in command-heavy references
- Bash syntax and helper `--help` smoke tests
- basic permission hygiene
- PowerShell parser validation when `pwsh` or `powershell` is installed

`tests/validate-links.sh` is optional and requires internet access plus `curl`. It treats 2xx, 3xx, 401, and 403 as reachable because vendor documentation sometimes blocks anonymous HEAD requests.

PowerShell syntax was not validated in environments where no PowerShell runtime is present. Run:

```powershell
pwsh -NoProfile -File tests/validate-powershell-syntax.ps1
```

## Live validation note - 2026-07-08

External links were validated through web retrieval because local curl-based validation could not resolve external DNS in the packaging container. See `tests/reports/live-validation-2026-07-08.md`.

PowerShell parser validation with `pwsh`/`powershell` was not possible in this environment. The package still includes `tests/validate-powershell-syntax.ps1` for validation on a host with PowerShell installed.
