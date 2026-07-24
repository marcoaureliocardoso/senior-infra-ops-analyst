# Container Runtime Operations Reference

Use this for Docker, containerd, Podman, CRI-O, image/runtime issues, container logs, host-level cgroups, volumes, networks, and runtime health beyond Kubernetes control-plane checks.

## Safety rules

- Prefer `ps`, `inspect`, `logs --tail`, `stats --no-stream`, and runtime metadata before exec/restart.
- Treat env vars, labels, mounts, image names, registry URLs, and logs as `SENSITIVE_OUTPUT`.
- `exec`, debug shells, image pulls, restarts, prune, rm, stop, kill, and network changes require explicit approval. A broad request to troubleshoot is not approval; the approval must identify the exact action, target, and scope.
- Do not dump full logs or environment variables. Redact secrets and tokens.

## Read-only checks

### Docker

```bash
docker version
docker info
docker ps --all --no-trunc
docker inspect <container>
docker logs --tail 200 --timestamps <container>
docker stats --no-stream
docker network ls
docker volume ls
```

Interpretation:
- Restart count rising -> crash loop or failing health check.
- `OOMKilled=true` -> memory limit or leak.
- Port mapping absent/mismatched -> exposure/routing issue.
- Bind mount missing or permission denied -> host filesystem issue.

### Podman

```bash
podman version
podman ps --all
podman inspect <container>
podman logs --tail 200 <container>
podman stats --no-stream
podman system df
```

### containerd / CRI

```bash
crictl info
crictl ps -a
crictl inspect <container-id>
crictl logs --tail=200 <container-id>
ctr namespaces list
```

## Active checks

- `curl` from host to an exposed port is `SAFE_READ_ONLY` + `ACTIVE_PROBE`.
- A narrowly scoped, non-mutating `docker exec` or `podman exec` is at least
  `LOW_RISK_CHANGE` + `REMOTE_SESSION_RISK` because it starts a process in the
  container. The invoked command inherits any higher plausible base level and
  applicable modifiers. Require explicit approval for the exact command and
  target.
- Image pull is `LOW_RISK_CHANGE`; restart or recreate is `DISRUPTIVE_CHANGE`; prune is `DESTRUCTIVE`.

## Evidence to capture

Runtime, host, container ID/name, image digest, restart count, health status, port mapping, mount list, last log excerpt, resource usage, and exact risk classification.

## Related references

- `references/kubernetes-operations.md`
- `references/linux-diagnostics.md`
- `references/monitoring-stack-operations.md`
