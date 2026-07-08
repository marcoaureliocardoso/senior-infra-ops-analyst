# SLO Specification

Use this to define one SLO that maps to user-visible reliability. Prefer a small number of meaningful SLOs over many noisy technical metrics.

| Field | Value | Guidance |
|---|---|---|
| Service |  | Name the service or user journey, not just the host. |
| User journey |  | Example: login, DNS resolution, file access, VPN connection. |
| SLI |  | Quantitative reliability indicator. Example: successful requests / valid requests. |
| Formula | good events / total valid events | Define good and valid events precisely. |
| Data source/query |  | Metric, log query, probe, or synthetic check. |
| Target |  | Example: 99.9% over 30 days. |
| Window |  | Rolling 7/28/30 days or calendar month. |
| Error budget |  | 100% - target. Example: 0.1% monthly. |
| Burn-rate alerts |  | Fast burn + slow burn, with runbook. |
| Dashboard |  | Link/name of dashboard panel. |
| Runbook |  | First diagnostic steps and escalation. |
| Owner |  | Team/person accountable. |
| Known gaps |  | Missing instrumentation, sampling limits, false positives. |

## Example

| Field | Value | Guidance |
|---|---|---|
| Service | Campus DNS resolver |  |
| User journey | Resolve internal and external names from client VLANs |  |
| SLI | successful DNS responses / valid DNS queries | Exclude blocked policy domains if intentional. |
| Target | 99.9% over 30 days |  |
| Burn-rate alerts | page on fast burn; ticket on slow burn |  |

## Validation questions

- Does the SLI reflect user pain?
- Can the data source be trusted during partial outages?
- Does the alert lead to a known action?
- Is there a dashboard and a runbook?
