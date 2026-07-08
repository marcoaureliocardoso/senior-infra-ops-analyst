# Live Validation Report - 2026-07-08

Scope: `references/external-sources.md` from `senior-infra-ops-analyst` v0.3.3.

## Method

- Local `curl` validation was attempted first, but the container could not resolve external DNS (`Could not resolve host`).
- Live validation therefore used web retrieval/search.
- Direct web retrieval was treated as `PASS_DIRECT` when the target URL loaded readable content.
- Search-confirmed official replacements were used when a target existed but direct fetch failed due to fetcher limitations, redirects, robots restrictions, or vendor site behavior.
- PowerShell syntax validation with a real parser was attempted only if `pwsh` or `powershell` was locally available.

## Summary

- URLs checked: 80
- Direct web retrieval passes: 72
- URLs needing replacement or alternate canonical URL: 8
- Remaining caveat: vendor sites can still block non-browser fetchers; use `tests/validate-links.sh` from a networked workstation for independent confirmation.
- PowerShell parser validation: not executed in this environment because neither `pwsh` nor `powershell` is installed, and the container cannot resolve external DNS to install PowerShell.

## Replacements applied in v0.3.4

| Original URL | Result | Replacement |
|---|---:|---|
| `https://docs.netgate.com/pfsense/en/latest/diagnostics/packetcapture.html` | direct fetch failed | `https://docs.netgate.com/pfsense/en/latest/diagnostics/packetcapture/index.html` |
| `https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname` | direct fetch failed without explicit view | `https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname?view=windowsserver2025-ps` |
| `https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent` | direct fetch failed without explicit view | `https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent?view=powershell-7.6` |
| `https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/repadmin` | direct fetch failed/current command page unavailable | `https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/diagnose-replication-failures` |
| `https://techdocs.broadcom.com/us/en/vmware-cis/vsphere.html` | direct fetch failed/403-style behavior | `https://knowledge.broadcom.com/external/article/344682/troubleshooting-an-esxi-host-in-a-not-re.html` |
| `https://www.freedesktop.org/software/systemd/man/latest/systemctl.html` | direct fetch failed in this validator | `https://www.freedesktop.org/software/systemd/man/systemctl.html` |
| `https://www.freedesktop.org/software/systemd/man/latest/journalctl.html` | direct fetch failed in this validator | `https://man7.org/linux/man-pages/man1/journalctl.1.html` |
| `https://www.tcpdump.org/manpages/tcpdump.1.html` | blocked by robots for this fetcher | `https://man7.org/linux/man-pages/man8/tcpdump.8.html` |

## PowerShell parser validation

Real parser validation was not possible here:

```text
command -v pwsh       -> not found
command -v powershell -> not found
container DNS         -> cannot resolve external hosts, so PowerShell could not be installed
```

To validate on a Windows or PowerShell-enabled Linux host:

```powershell
pwsh -NoProfile -File tests/validate-powershell-syntax.ps1
```

Expected successful result:

```text
PowerShell syntax validation passed
```

## Notes

This report records live validation performed during packaging. It is not a guarantee of future link availability. Vendor URLs, especially Broadcom/VMware and Microsoft Learn pages with `view=` selectors, can change or apply bot restrictions.
