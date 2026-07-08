# Example: Quarterly VPN Admin Access Review Evidence

## Scenario

Quarterly audit evidence is required for privileged VPN administration access. Scope is the `vpn-admins` identity group, the pfSense admin role mapping, and the last 90 days of membership changes. The goal is evidence collection only; no access removal is performed during collection.

## Control objective

Only approved infrastructure operators should retain privileged VPN administration access, and every retained member should have a current business justification and accountable owner.

## Evidence collected

| Evidence | Command/source | Risk | Result summary |
|---|---|---|---|
| Identity group membership | `Get-ADGroupMember vpn-admins` or IdP group export | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | 6 active members, 1 service account, 0 disabled users. |
| Recent membership changes | AD/IdP audit log query for group changes in last 90 days | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | 2 additions, both tied to approved tickets. |
| Firewall role mapping | pfSense user/group privilege review or exported config snippet | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | `vpn-admins` maps to VPN and firewall diagnostics privileges. |
| Ticket approvals | ITSM tickets `CHG-1842`, `REQ-7781` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Approver, owner, and expiration date present. |
| Last interactive use | VPN/authentication logs scoped to named accounts | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | 1 account unused for 112 days. |

## Interpretation

The control is mostly effective. Active users have approval evidence, but one stale account should be reviewed by the access owner before the next audit checkpoint. The service account requires a separate non-human account justification and credential rotation evidence.

## Exceptions and follow-up

| Finding | Severity | Owner | Due date | Action |
|---|---|---|---|---|
| Stale privileged account unused for 112 days | Medium | Network lead | 7 days | Confirm business need or remove via approved access-change ticket. |
| Service account lacks explicit rotation evidence | Medium | Infrastructure lead | 14 days | Attach rotation record or open remediation ticket. |

## Evidence handling

Store screenshots/exports in the audit evidence repository with restricted access. Redact user personal data not needed for the control assertion. Record hashes for exported CSV/PDF files if evidence immutability is required.
