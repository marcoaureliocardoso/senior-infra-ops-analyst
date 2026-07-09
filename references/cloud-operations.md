# Cloud Operations Reference

Use this when diagnosing AWS, Azure, or GCP resources. Prefer narrow scopes: account/subscription/project, region/zone, resource group, VPC/VNet/network, instance name, and time window.

## Global risk rules

| Action | Risk |
|---|---|
| account/project identity check | SAFE_READ_ONLY |
| scoped list/describe/show/get | SAFE_READ_ONLY |
| logs/activity/IAM/security-rule review | SAFE_READ_ONLY + SENSITIVE_OUTPUT |
| broad inventory across all regions/projects | SAFE_READ_ONLY + RESOURCE_INTENSIVE + SENSITIVE_OUTPUT |
| start/stop/reboot/resize/delete | DISRUPTIVE_CHANGE or DESTRUCTIVE |
| IAM, firewall, route, load balancer, DNS, backup, autoscaling changes | DISRUPTIVE_CHANGE |
| restore overwrite, snapshot deletion, key deletion | DESTRUCTIVE |

## AWS safe checks

```bash
aws sts get-caller-identity
aws configure list
aws ec2 describe-instances --region <region> --instance-ids <instance-id>
aws ec2 describe-instance-status --region <region> --instance-ids <instance-id> --include-all-instances
aws ec2 describe-volumes --region <region> --filters Name=attachment.instance-id,Values=<instance-id>
aws ec2 describe-security-groups --region <region> --group-ids <sg-id>
aws ec2 describe-route-tables --region <region> --filters Name=vpc-id,Values=<vpc-id>
aws elbv2 describe-target-health --region <region> --target-group-arn <target-group-arn>
aws cloudwatch describe-alarms --region <region> --state-value ALARM
```

Sensitive or scoped checks:

```bash
aws logs filter-log-events --region <region> --log-group-name <group> --start-time <epoch-ms> --end-time <epoch-ms> --limit 50
aws iam get-role --role-name <role>
aws iam list-attached-role-policies --role-name <role>
```

Interpretation:

- Instance status failing: provider/host/OS check may be impaired; compare system vs instance status.
- Target unhealthy but instance running: load balancer health path, security group, service port, or app health issue.
- Security group allows broad management access: exposure risk, not necessarily outage cause.
- Volume full/IO impaired symptoms: correlate with OS disk metrics and CloudWatch.

## Azure safe checks

```bash
az account show
az group show --name <resource-group>
az vm show --resource-group <resource-group> --name <vm-name>
az vm get-instance-view --resource-group <resource-group> --name <vm-name>
az vm list-ip-addresses --resource-group <resource-group> --name <vm-name>
az network nsg list --resource-group <resource-group>
az network route-table list --resource-group <resource-group>
az monitor metrics list --resource <resource-id> --metric "Percentage CPU"
az monitor activity-log list --resource-group <resource-group> --max-events 50
```

Sensitive or scoped checks:

```bash
az role assignment list --scope <scope>
az monitor log-analytics query --workspace <workspace-id> --analytics-query '<query>'
```

Interpretation:

- VM running but service unreachable: check NSG, route table, public/private IP, guest firewall, and service listener.
- Activity log around incident start: look for redeploy, resize, NSG, route, identity, or disk operations.
- Role assignments broad or inherited: access exposure; handle as sensitive evidence.

## GCP safe checks

```bash
gcloud auth list
gcloud config list
gcloud compute instances list --project <project> --filter='name=<instance-name>'
gcloud compute instances describe <instance-name> --project <project> --zone <zone>
gcloud compute disks list --project <project> --filter='users:<instance-name>'
gcloud compute firewall-rules list --project <project> --filter='network=<network>'
gcloud compute routes list --project <project> --filter='network=<network>'
gcloud compute backend-services get-health <backend-service> --project <project> --global
```

Sensitive or scoped checks:

```bash
gcloud logging read '<filter>' --project <project> --limit 50 --freshness=1h
gcloud projects get-iam-policy <project>
```

Interpretation:

- Instance listed but health failing: compare guest OS, serial/ops-agent signals, firewall, routes, and backend health.
- Firewall rule broad source ranges: exposure risk; confirm whether it is required before recommending changes.
- IAM policy review can expose people/groups/service accounts; summarize and redact.

## Change approval reminders

Before any cloud change, provide:

- Exact command/API action
- Target resources
- Expected effect
- Blast radius
- Rollback command or recovery path
- Validation command
- Audit evidence to retain

## Provider-native active probes

| Provider | Command | Risk | Interpretation |
|---|---|---|---|
| Azure | `az network watcher test-connectivity --resource-group <rg> --source-resource <vm-id> --dest-address <host> --dest-port <port>` | SAFE_READ_ONLY + ACTIVE_PROBE + SENSITIVE_OUTPUT | Tests connectivity from Azure perspective; may reveal topology. |
| GCP | `gcloud compute network-management connectivity-tests describe <test-name> --project <project>` | SAFE_READ_ONLY + SENSITIVE_OUTPUT | Reads configured connectivity test results. Creating tests is a change. |
| AWS | `aws ec2 describe-network-insights-analyses --network-insights-analysis-ids <id>` | SAFE_READ_ONLY + SENSITIVE_OUTPUT | Reads existing reachability analysis. Creating analyses may require approval. |

## Safety rules

- Treat IAM, activity logs, security rules, routes, and logging queries as `SENSITIVE_OUTPUT`.
- Treat all broad cross-region, cross-subscription, or cross-project inventory as `RESOURCE_INTENSIVE + SENSITIVE_OUTPUT`.
- Treat provider-native connectivity tests and health probes as `ACTIVE_PROBE` unless they only read existing results.
- Never execute start/stop/reboot/resize/delete, IAM changes, security rule changes, DNS changes, or backup/restore actions without explicit approval.
- Summarize and redact identities, public IPs, internal IPs, resource IDs, and policy details when sharing outside the operations context.

## Pagination and JSON extraction

Cloud CLIs can return large result sets. Prefer scope filters, provider pagination controls, and field extraction before broad dumps. Examples:

```bash
aws ec2 describe-instances --filters "Name=tag:Name,Values=<name>" --max-results 50 | jq '.Reservations[].Instances[] | {InstanceId,State,PrivateIpAddress,PublicIpAddress}'
az vm list -g <rg> --query '[].{name:name,powerState:powerState,privateIps:privateIps}' -o json | jq .
gcloud compute instances list --filter='name=<name>' --format=json | jq '.[] | {name,zone,status,networkInterfaces}'
```

Risk: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`; public/private IPs, account IDs, project names, and tags may need redaction.

## Related references

- `references/network-diagnostics.md`
- `references/storage-backup.md`
- `references/pki-certificate-lifecycle.md`
- `references/monitoring-stack-operations.md`
- `references/ssh-privileged-access.md`
