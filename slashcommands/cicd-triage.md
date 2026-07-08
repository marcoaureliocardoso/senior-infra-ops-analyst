---
description: "Diagnose CI/CD pipeline failures, runner capacity, artifact problems, deployment gate failures, and release safety issues."
---
# /cicd-triage

Purpose: diagnose CI/CD pipeline failures, runner capacity, artifact problems, deployment gate failures, or release safety issues.

Expected input:
- platform, repo/project, run/pipeline/job ID, failed stage, environment, time window.

Behavior:
- Use `skills/cicd-operations/SKILL.md`.
- Use `skills/cicd-operations/templates/pipeline-incident.md`.
- Treat logs, artifact names, runner details, and secrets as sensitive.
- Do not rerun deployment jobs, approve gates, rotate secrets, cancel production jobs, or rollback without approval.

Example:
`/cicd-triage GitLab project 123 pipeline 456 failed during deploy to staging`
