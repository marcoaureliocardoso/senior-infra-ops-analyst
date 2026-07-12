---
description: "Diagnose AWS, Azure, or GCP resources using scoped read-only cloud CLI and API commands."
allowed-tools: Task(subagent_type:cloud-platform-operator)
---
# /cloud-check

Use the Cloud Operations and Command Driven Operations skills.

## Purpose

Diagnose AWS, Azure, or GCP resources using scoped read-only cloud CLI/API commands.

## Expected input

- Provider: AWS, Azure, or GCP
- Account/subscription/project
- Region/zone/resource group
- Target resource
- Symptom and time window

## Behavior

1. Confirm identity and scope.
2. Run only scoped read/list/describe/show/get commands.
3. Treat logs, IAM, security rules, public IPs, and billing as sensitive.
4. Interpret findings by compute, network, identity, storage, monitoring, quota, backup, or dependency.
5. Stop before state-changing actions.

## Example

`/cloud-check AWS instance i-0123 in us-east-1 is unreachable on 443 since 10:15`

## Output

Cloud scope, commands executed, evidence, interpretation, blast radius, next safe checks, approval-required actions.
