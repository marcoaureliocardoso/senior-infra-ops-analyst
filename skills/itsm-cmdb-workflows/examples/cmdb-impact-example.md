# Example: CMDB Impact Check Before Firewall Change

## Scenario

A firewall rule change is requested to restrict outbound SMTP from a server subnet. Before implementation, the operator must identify affected services and confirm the change ticket has accurate CI relationships.

## Evidence collected

| Step | Source/query | Risk | Observed result |
|---|---|---|---|
| Locate affected subnet CI | CMDB search for subnet `10.20.30.0/24` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Subnet CI linked to `Academic Systems` service group. |
| Find dependent servers | CMDB relationship query: subnet -> server CIs | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | 14 servers attached; 3 tagged as mail relay clients. |
| Check service ownership | ITSM service map for linked applications | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Owners identified for Portal, Moodle, Library System. |
| Review recent incidents | ITSM query for incidents involving SMTP or mail relay in last 30 days | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | 2 incidents tied to blocked mail relay tests. |
| Check change completeness | Ticket `CHG-2219` fields | `SAFE_READ_ONLY` | Rollback exists; communication plan missing one owner. |

## Interpretation

The requested firewall change has a broader service impact than the ticket initially states. Three applications depend on SMTP relay behavior from the subnet. The change can proceed only after owner notification and validation tests are added.

## Required ticket updates

- Add impacted CIs: `portal-app-02`, `moodle-worker-01`, `library-api-01`.
- Add affected services and owners.
- Add pre/post validation: test SMTP relay from approved hosts and confirm denied traffic from unapproved hosts.
- Add communication to application owners at least one business day before implementation.

## Approval gate

Do not update CMDB relationships or approve the change automatically. These actions are `LOW_RISK_CHANGE` + `EXTERNAL_SIDE_EFFECT` and require the normal ITSM workflow.
