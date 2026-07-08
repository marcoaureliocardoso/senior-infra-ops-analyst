# Cloud Command Record Examples

## AWS

| Field | Value |
|---|---|
| Target | EC2 instance `<instance-id>` in `<region>` |
| Command | `aws ec2 describe-instance-status --region <region> --instance-ids <instance-id> --include-all-instances` |
| Risk | SAFE_READ_ONLY |
| Purpose | Check provider and instance status before OS-level diagnosis. |
| Interpretation | Failed system check suggests provider/host issue; failed instance check suggests guest OS/network/service issue. |

## Azure

| Field | Value |
|---|---|
| Target | VM `<vm-name>` in resource group `<resource-group>` |
| Command | `az vm get-instance-view --resource-group <resource-group> --name <vm-name>` |
| Risk | SAFE_READ_ONLY |
| Purpose | Check VM power/provisioning/extension status. |
| Interpretation | Running VM with failed extension/agent points to guest or management-plane issue. |

## GCP

| Field | Value |
|---|---|
| Target | Compute Engine instance `<instance-name>` in `<zone>` |
| Command | `gcloud compute instances describe <instance-name> --project <project> --zone <zone>` |
| Risk | SAFE_READ_ONLY + SENSITIVE_OUTPUT |
| Purpose | Inspect status, network interfaces, disks, labels, and metadata scope. |
| Interpretation | Instance running with blocked service usually points to guest firewall, VPC firewall, route, backend health, or service listener. |
