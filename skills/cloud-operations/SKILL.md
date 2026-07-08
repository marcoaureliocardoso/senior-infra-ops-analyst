---
name: Cloud Operations
skill_id: cloud-operations
description: Use when operating or diagnosing AWS, Azure, or GCP infrastructure with CLI/API access, especially inventory, VM health, network rules, load balancers, IAM exposure, monitoring, logs, quotas, backup, cost, and safe cloud change planning.
version: 0.4.1
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - aws check
  - azure check
  - gcp check
  - cloud inventory
  - cloud incident
---

# Cloud Operations

Operate cloud environments with the same command-driven safety model used for on-prem infrastructure.

<required>
1. Identify provider, account/subscription/project, region/zone, resource group/VPC/VNet/network, environment, permissions, and production impact.
2. Execute narrowly scoped read/list/describe commands when tool access exists; never enumerate broadly when a scoped target is known.
3. Treat IAM, logs, security groups, NSGs, firewall rules, public IPs, route tables, snapshots, backups, and billing data as sensitive operational evidence.
4. Do not execute start/stop/reboot/resize/delete/modify, IAM policy changes, network changes, backup restore, failover, or autoscaling changes without explicit approval.
5. For every cloud finding, identify whether the issue is compute, identity, network, storage, quota, managed service, monitoring, backup, region/zone, or external dependency.
6. Include blast radius, rollback path, validation command, and audit evidence for every proposed cloud change.
</required>

## Command sources

Use `references/cloud-operations.md` for AWS, Azure, and GCP commands, risk levels, and interpretation.

## Diagnostic order

1. Confirm identity and scope.
2. Inventory affected resource only.
3. Check resource health/status.
4. Check network exposure/path.
5. Check logs/metrics in narrow time window.
6. Check IAM/permission symptoms if access-related.
7. Check quota, capacity, backup, region/zone, and recent changes.
8. Stop before state-changing mitigation unless approval is explicit.

## Required references

- `references/risk-levels.md`
- `references/cloud-operations.md`


## Output

Return:

- Cloud scope confirmed
- Commands executed
- Observed evidence
- Interpretation by cloud layer
- Risk and blast radius
- Next safe checks
- Approval-required actions
