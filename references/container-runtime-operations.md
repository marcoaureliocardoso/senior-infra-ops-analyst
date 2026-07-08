# Container Runtime Operations Reference

Use this for Docker, containerd, Podman, CRI-O, image/runtime issues, container logs, host-level cgroups, volumes, networks, and runtime health beyond Kubernetes control-plane checks.

## Safety rules

- Prefer `ps`, `inspect`, `logs --tail`, `stats --no-stream`, and runtime metadata before exec/restart.
- Treat env vars, labels, mounts, image names, registry URLs, and logs as `SENSITIVE_OUTPUT`.
- `exec`, debug shells, image pulls, restarts, prune, rm, stop, kill, and network changes require approval unless explicitly requested.
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

- `curl` from host to exposed port is `ACTIVE_PROBE`.
- `docker exec` or `podman exec` is `REMOTE_SESSION_RISK` and may alter access/session state; approval recommended.
- Restart/recreate/pull/prune is `STATE_CHANGING` or `DESTRUCTIVE`.

## Evidence to capture

Runtime, host, container ID/name, image digest, restart count, health status, port mapping, mount list, last log excerpt, resource usage, and exact risk classification.
