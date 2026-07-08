# Example: Docker Container Restart Loop on Single Host

## Scenario

A standalone Docker host runs `inventory-api`. The service is intermittently unavailable and the container restarts repeatedly. This is outside Kubernetes; use container runtime and host diagnostics only.

## Evidence sequence

| Step | Command | Risk | Observed result |
|---|---|---|---|
| List container state | `docker ps --filter name=inventory-api --no-trunc` | `SAFE_READ_ONLY` | Container restarts every 20-30 seconds. |
| Inspect restart policy | `docker inspect inventory-api --format '{{json .HostConfig.RestartPolicy}}'` | `SAFE_READ_ONLY` | `always` restart policy. |
| Read recent logs | `docker logs --tail=200 --timestamps inventory-api` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | App exits after `ECONNREFUSED` to database endpoint. |
| Check resource pressure | `docker stats --no-stream inventory-api` | `SAFE_READ_ONLY` | CPU/memory normal before exit. |
| Check host disk | `df -h` | `SAFE_READ_ONLY` | `/var/lib/docker` has 78% usage, not full. |
| Check runtime health | `systemctl status docker --no-pager` | `SAFE_READ_ONLY + PRIVILEGED` | Docker service healthy. |

## Interpretation

The runtime is keeping the container alive as designed, but the application process exits because a dependency is refusing database connections. The immediate next branch is dependency reachability and application configuration, not Docker daemon restart.

## Safe next actions

- Verify the configured database host/port from sanitized environment output.
- Test TCP connectivity from the host or a temporary approved diagnostic container.
- Compare current container image tag and environment with last known good deployment record.

## Approval gate

Do not run `docker restart`, recreate volumes, prune images, or change environment variables without approval. Restarting may temporarily mask the failure and destroy useful evidence.
