# CI/CD Operations Reference

Use this for failed pipelines, runner capacity, artifact problems, deployment gates, rollback workflow health, secret exposure risk, and release safety.

## Safety rules

- Treat job logs, environment variables, artifact names, repository names, and deployment targets as `SENSITIVE_OUTPUT`.
- Do not rerun failed deployment jobs, approve gates, rotate secrets, invalidate caches, or rollback without explicit approval.
- Prefer read-only pipeline/job/run inspection and exact failing step identification.
- Never paste secrets from logs; redact tokens and credentials.

## Read-only checks

### GitHub Actions

```bash
gh run list --limit 20
gh run view <run-id> --log-failed
gh workflow list
gh api repos/<owner>/<repo>/actions/runners
```

Interpretation:
- Same failure across jobs -> shared dependency, runner image, secret, or upstream outage.
- One job fails after code change -> likely repo/application issue.
- Queue time rising -> runner capacity or concurrency issue.

### GitLab CI

```bash
gitlab-runner --version
gitlab-runner list
curl --header "PRIVATE-TOKEN: <redacted>" "https://gitlab.example/api/v4/projects/<id>/pipelines"
```

### Jenkins

```bash
java -jar jenkins-cli.jar -s <url> who-am-i
java -jar jenkins-cli.jar -s <url> list-jobs
java -jar jenkins-cli.jar -s <url> console <job> <build>
```

## Shell-history warning

Avoid placing bearer tokens, private tokens, cookies, or credentials directly on the command line because they can be captured in shell history, process listings, terminal logs, or audit tooling.
Prefer approved secret stores, short-lived environment variables, `--netrc`/credential helpers where appropriate, or vendor CLI authentication. Redact tokens from examples and outputs.

## Risk mapping

- List/view runs and failed logs: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Rerun, cancel, approve, deploy, rollback: `STATE_CHANGING` or `DISRUPTIVE`.
- Secret rotation: `STATE_CHANGING` + high sensitivity.

## Evidence to capture

Pipeline URL/ID, commit SHA, actor, environment, failed stage, first failing line after redaction, runner, dependency/service status, and rollback option.

## Related references

- `references/container-runtime-operations.md`
- `references/kubernetes-operations.md`
- `references/cloud-operations.md`
- `skills/change-management/SKILL.md`
