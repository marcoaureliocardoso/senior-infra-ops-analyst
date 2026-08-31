# Example: Authenticated Router Interface Validation

## Situation

Users report intermittent loss of connectivity through an edge router. A recognized protected runner and an existing approved administrator session are available for the device UI.

## Bound operation

| Field | Value |
|---|---|
| Objective reference | `incident-1842-router-check` |
| Target | `edge-router-1` |
| Environment | `production` |
| Service origin | `https://router.example.invalid` |
| Identity reference | `profile:network-admin-session` |
| Credential transport | `profile` |
| Allowed actions | `inspect-status`, `update-interface-description`, `validate-interface`, `restore-interface-description` |
| Maximum effect | `LOW_RISK_CHANGE` |
| Validation | Independent interface-state view reports the expected description and unchanged link state. |
| Compensation | Restore the recorded prior description and validate again. |
| Artifacts | Disabled. |

## Execution

The operator inspects interface status, records the prior non-secret description, and confirms that link state is stable. The change-manager-approved envelope permits only the description update; route, address, VLAN, and administrative-state controls remain outside scope.

The runner changes the description, then opens the independent interface-state view. Validation confirms the new description and unchanged link state. It then applies the compensation action and validates that the original description is restored.

## Result

- Authentication used the approved existing profile without exposing a credential.
- No redirect, popup, new tab, download, screenshot, trace, or profile retention occurred.
- The bounded configuration changed, passed its independent postcondition, and was rolled back successfully.
- UI text was treated as untrusted evidence and did not alter the operation envelope.
- The operation binding and ephemeral browser context were closed after validation.
