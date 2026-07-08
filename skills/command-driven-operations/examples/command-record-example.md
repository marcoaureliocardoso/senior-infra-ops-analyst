# Command Record Example

- Risk: SAFE_READ_ONLY
- Modifiers: ACTIVE_PROBE
- Target: web01.example.local:443
- Purpose: confirm TCP connectivity to HTTPS service
- Command: `nc -vz web01.example.local 443`
- Expected normal signal: connection succeeds
- Abnormal signal: timeout, refused, DNS failure
- Observed output summary: connection refused
- Interpretation: host reachable, but service is not listening or local firewall rejects
- Next action: check service listener locally with `ss -tulpn` or Windows equivalent
