# Example: CI/CD Pipeline Failure After Container Build Step

## Scenario

The `portal-api` production deployment pipeline failed after a merge to `main`. The failure occurred before deployment, so no production state was changed. Scope is pipeline diagnostics and artifact availability only.

## Evidence sequence

| Step | Command/source | Risk | Observed result |
|---|---|---|---|
| Identify failed stage | CI job summary for run `#8421` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Failed in `build-image`; deploy stage did not start. |
| Inspect recent commit | `git show --stat --oneline HEAD` | `SAFE_READ_ONLY` | Dockerfile and dependency lockfile changed. |
| Read job log tail | CI job log, last 200 lines | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Registry returned `manifest unknown` for base image tag. |
| Check runner health | Runner status page or `gitlab-runner list`/provider runner view | `SAFE_READ_ONLY` | Runner online; no broad runner outage. |
| Check registry auth | CI variables metadata, not secret values | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Registry credential variable present and unexpired. |

## Interpretation

The pipeline failure is most likely caused by an invalid or removed base-image tag, not by runner capacity, registry authentication, or deployment logic. Because the deploy stage never executed, rollback is not required.

## Safe next actions

1. Confirm the expected base-image tag with the application owner.
2. Re-run build in a non-production branch using a pinned valid image digest.
3. Open a change or pull request to pin the base image to an approved digest.
4. Re-run the pipeline after code review.

## Approval gate

Do not manually push replacement images to the production registry and do not bypass CI approvals. Any manual artifact promotion is `DISRUPTIVE_CHANGE` and requires explicit approval plus audit trail.

## Output record

- Incident/ticket: `INC-2451`
- Pipeline: `portal-api/main/#8421`
- Failed stage: `build-image`
- Probable cause: invalid base-image tag
- Customer impact: none observed; release delayed
- Next owner: application team
