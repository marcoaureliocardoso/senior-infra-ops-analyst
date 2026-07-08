---
name: CI/CD Operations
description: Use when diagnosing failed pipelines, runner capacity, deployment gates, artifact failures, rollback workflows, or release safety issues.
version: 0.4.1
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - cicd-operations
  - ci/cd operations
---

# CI/CD Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify platform, repository/project, pipeline ID, branch/tag, environment, runner/executor, deployment target, and release impact.
2. Use `references/cicd-operations.md` to inspect pipeline status, jobs, runners, artifacts, caches, secrets references, approvals, and deployment history.
3. Cross-reference container runtime, Kubernetes, cloud, web gateway, and database references when deployment failures surface downstream.
4. Treat logs, variables, tokens, artifact names, image tags, commit metadata, and environment names as `SENSITIVE_OUTPUT`.
5. Prefer read-only CLI/API queries for workflow/job status, runner health, artifact availability, and recent deployment history before reruns or rollback.
6. Interpret failures by stage: source checkout, dependency install, test, build, artifact, registry, deploy gate, runner capacity, credential, or target health.
7. Require approval before rerun with side effects, cancel, rollback, promote, force deploy, clear cache, rotate secret, or modify pipeline definitions.
8. Classify deployment actions and rollback paths with shared risk levels, and require validation criteria before any state change.
9. Produce `skills/cicd-operations/templates/pipeline-incident.md` with pipeline evidence, failed stage, likely layer, approval gate, and validation plan.
</required>

## Output

Return:
- Situation and scope
- Domain-specific command/evidence sequence
- Commands executed or explicitly not executed
- Observations and interpretation
- Risk classification and modifiers
- Recommended next action
- Approval gate, if needed
- Completed template artifact

## References

- `references/cicd-operations.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
