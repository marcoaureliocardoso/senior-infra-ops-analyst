# External Sources

Use these official references when updating or validating this skillset. Prefer vendor documentation, standards, and public SRE material. Do not copy commands blindly: apply the skillset risk model, scope controls, redaction rules, and approval gates before execution.

## SRE / incident / observability

- Google SRE - Service Level Objectives: https://sre.google/sre-book/service-level-objectives/
- Google SRE Workbook - Implementing SLOs: https://sre.google/workbook/implementing-slos/
- Google SRE Workbook - Alerting on SLOs: https://sre.google/workbook/alerting-on-slos/
- Google SRE - Monitoring Distributed Systems: https://sre.google/sre-book/monitoring-distributed-systems/
- Google SRE Workbook - Incident Response: https://sre.google/workbook/incident-response/
- Google SRE - Postmortem Culture: https://sre.google/sre-book/postmortem-culture/

## Protocol standards / RFCs

- RFC 791 - Internet Protocol IPv4: https://www.rfc-editor.org/rfc/rfc791
- RFC 8200 - Internet Protocol IPv6: https://www.rfc-editor.org/rfc/rfc8200
- RFC 9293 - Transmission Control Protocol TCP: https://www.rfc-editor.org/rfc/rfc9293
- RFC 768 - User Datagram Protocol UDP: https://www.rfc-editor.org/rfc/rfc768
- RFC 8446 - TLS 1.3: https://www.rfc-editor.org/rfc/rfc8446
- RFC 9110 - HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110
- RFC 1034 - Domain Names Concepts and Facilities: https://www.rfc-editor.org/rfc/rfc1034
- RFC 1035 - Domain Names Implementation and Specification: https://www.rfc-editor.org/rfc/rfc1035
- RFC 2131 - DHCP for IPv4: https://www.rfc-editor.org/rfc/rfc2131
- RFC 8415 - DHCPv6: https://www.rfc-editor.org/rfc/rfc8415
- RFC 1918 - Private IPv4 Address Space: https://www.rfc-editor.org/rfc/rfc1918
- RFC 5737 - IPv4 Documentation Address Blocks: https://www.rfc-editor.org/rfc/rfc5737
- RFC 6890 - Special-Purpose IP Address Registries: https://www.rfc-editor.org/rfc/rfc6890

## Linux / Unix diagnostics

- Linux man-pages project: https://www.kernel.org/doc/man-pages/
- iproute2 documentation: https://wiki.linuxfoundation.org/networking/iproute2
- systemd systemctl manual: https://www.freedesktop.org/software/systemd/man/latest/systemctl.html
- systemd journalctl manual: https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- OpenSSH manual pages: https://www.openssh.com/manual.html
- tcpdump manual: https://www.tcpdump.org/manpages/tcpdump.1.html

## Windows Server / PowerShell diagnostics

- PowerShell documentation: https://learn.microsoft.com/en-us/powershell/
- Test-NetConnection: https://learn.microsoft.com/en-us/powershell/module/nettcpip/test-netconnection
- Resolve-DnsName: https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname
- Get-WinEvent: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent
- Windows Server DNS troubleshooting: https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-dns-guidance
- Windows DNS dynamic update troubleshooting: https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/troubleshooting-dns-dynamic-update-issues
- Active Directory replication concepts: https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/replication/active-directory-replication-concepts
- dcdiag reference: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/dcdiag
- repadmin reference: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/repadmin

## pfSense / firewall operations

- pfSense documentation home: https://docs.netgate.com/pfsense/en/latest/
- Troubleshooting firewall rules: https://docs.netgate.com/pfsense/en/latest/troubleshooting/firewall.html
- Troubleshooting NAT port forwards: https://docs.netgate.com/pfsense/en/latest/troubleshooting/nat-port-forwards.html
- Troubleshooting high availability: https://docs.netgate.com/pfsense/en/latest/troubleshooting/high-availability.html
- pfSense diagnostics menu guide: https://docs.netgate.com/pfsense/en/latest/menuguide/diagnostics.html
- Packet capture in pfSense: https://docs.netgate.com/pfsense/en/latest/diagnostics/packetcapture.html

## Kubernetes / K3s

- Kubernetes troubleshooting overview: https://kubernetes.io/docs/tasks/debug/
- Debug Pods: https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/
- Debug Running Pods: https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/
- Debug Services: https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/
- Troubleshooting Clusters: https://kubernetes.io/docs/tasks/debug/debug-cluster/
- kubectl command reference: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands
- K3s documentation: https://docs.k3s.io/

## VMware / virtualization

- VMware vSphere documentation: https://techdocs.broadcom.com/us/en/vmware-cis/vsphere.html
- ESXi performance troubleshooting: https://knowledge.broadcom.com/external/article/304594/troubleshooting-esxesxi-virtual-machine.html
- ESXi storage latency troubleshooting: https://knowledge.broadcom.com/external/article/318927/esxi-device-latency-with-performance-has.html

## Backup / recovery / resilience

- NIST SP 800-34 Rev. 1 - Contingency Planning Guide: https://csrc.nist.gov/publications/detail/sp/800-34/rev-1/final
- CIS Controls v8 overview: https://www.cisecurity.org/controls/v8
- AWS Backup documentation: https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- Azure Backup documentation: https://learn.microsoft.com/en-us/azure/backup/backup-overview
- Google Cloud Backup and DR documentation: https://cloud.google.com/backup-disaster-recovery/docs

## AWS operations

- AWS Well-Architected Framework: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
- AWS Well-Architected Reliability Pillar: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html
- AWS Well-Architected Change Management: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/change-management.html
- AWS Well-Architected Failure Management: https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-failmgmt.html
- AWS CLI Command Reference: https://docs.aws.amazon.com/cli/latest/reference/
- EC2 describe-instances: https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-instances.html
- EC2 describe-instance-status: https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-instance-status.html
- EC2 describe-volumes: https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-volumes.html
- CloudWatch describe-alarms: https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/describe-alarms.html
- VPC Reachability Analyzer: https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html

## Azure operations

- Azure Well-Architected Framework: https://learn.microsoft.com/en-us/azure/well-architected/
- Azure reliability recommendations: https://learn.microsoft.com/en-us/azure/advisor/advisor-reference-reliability-recommendations
- Azure CLI documentation: https://learn.microsoft.com/en-us/cli/azure/
- Azure VM CLI reference: https://learn.microsoft.com/en-us/cli/azure/vm
- Azure Monitor documentation: https://learn.microsoft.com/en-us/azure/azure-monitor/
- Azure Network Watcher: https://learn.microsoft.com/en-us/azure/network-watcher/network-watcher-monitoring-overview
- Azure Virtual Network architecture best practices: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/virtual-network

## Google Cloud operations

- Google Cloud Well-Architected Framework: https://cloud.google.com/architecture/framework
- Google Cloud Well-Architected Reliability pillar: https://cloud.google.com/architecture/framework/reliability
- Google Cloud Observability: https://cloud.google.com/products/observability
- Google Cloud Observability reliability guidance: https://cloud.google.com/architecture/framework/reliability/observability
- gcloud CLI reference: https://cloud.google.com/sdk/gcloud/reference
- gcloud compute instances list: https://cloud.google.com/sdk/gcloud/reference/compute/instances/list
- Compute Engine get/list instances: https://cloud.google.com/compute/docs/instances/get-list
- Network Intelligence Center: https://cloud.google.com/network-intelligence-center/docs
