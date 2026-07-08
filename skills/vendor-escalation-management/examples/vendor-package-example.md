# Example: ISP Escalation Package for Packet Loss

## Scenario

The backup internet link shows intermittent packet loss during business hours. Internal firewall and LAN checks do not show local drops. The operator needs to prepare an escalation package for the ISP.

## Evidence package

| Evidence | Command/source | Risk | Summary |
|---|---|---|---|
| Incident timeline | ITSM incident notes | `SAFE_READ_ONLY` | Loss observed 09:10-10:05 and 14:20-15:00. |
| Interface status | pfSense interface/status page or read-only CLI | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | WAN2 link stays up; no local interface flap. |
| Gateway monitoring | pfSense gateway logs/RRD | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Packet loss spikes to 18%; latency increases to 250 ms. |
| Path test | `mtr -rw <ISP gateway or approved target>` | `SAFE_READ_ONLY + ACTIVE_PROBE` | Loss begins after ISP next hop. |
| Local comparison | LAN-to-firewall and primary WAN checks | `SAFE_READ_ONLY + ACTIVE_PROBE` | LAN and primary WAN normal during same window. |
| Change correlation | Internal change calendar | `SAFE_READ_ONLY` | No internal network change in window. |

## Vendor request

Ask the ISP to investigate intermittent packet loss beyond the customer edge on the backup circuit. Include circuit ID, timestamps with timezone, source/destination of tests, MTR output, gateway monitoring graph, and confirmation that CPE interface remained up.

## Escalation boundaries

Do not provide firewall configuration exports, internal subnet inventory, packet captures containing payloads, or credentials. Redact internal hostnames unless the vendor contract requires them.

## Success criteria

- Vendor acknowledges circuit and timestamps.
- Vendor checks access circuit and upstream path.
- Vendor provides root cause or maintenance reference.
- Follow-up monitoring confirms loss resolved for one business day.
