# Example: Branching Playbook — VPN User Cannot Reach Internal System

## Purpose

Guide a service desk or infrastructure operator through safe diagnosis of a VPN connectivity complaint.

## Prerequisites

- User identity or ticket number
- VPN username or assigned IP
- Target internal host and port
- Read-only access to VPN logs/status and firewall logs

## Decision tree

| Decision | Check | Interpretation | Next step |
|---|---|---|---|
| User connected? | VPN session list for username | No active session | Ask user to reconnect; check auth logs. |
| Address assigned? | VPN session details | No IP or wrong pool | Check pool exhaustion/config. |
| Route present? | Client route table or VPN profile | Missing route | Escalate to VPN profile/config owner. |
| Port reachable? | `Test-NetConnection <target> -Port <port>` | Timeout | Check firewall/VPN policy path. |
| Service listening? | Server-side listener check | Refused/down | Escalate to application/server owner. |

## Safety gates

- Do not reset user MFA, alter VPN groups, change firewall policy, or restart VPN service without approval.
- Redact usernames, public IPs, and internal addresses when sharing externally.

## Expected output

A ticket note with facts, commands executed, observed result, likely layer, next owner, and whether approval is needed for any change.
