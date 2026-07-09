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

- RFC 791 - Internet Protocol IPv4: https://datatracker.ietf.org/doc/html/rfc791
- RFC 8200 - Internet Protocol IPv6: https://datatracker.ietf.org/doc/html/rfc8200
- RFC 9293 - Transmission Control Protocol TCP: https://datatracker.ietf.org/doc/html/rfc9293
- RFC 768 - User Datagram Protocol UDP: https://datatracker.ietf.org/doc/html/rfc768
- RFC 8446 - TLS 1.3: https://datatracker.ietf.org/doc/html/rfc8446
- RFC 9110 - HTTP Semantics: https://datatracker.ietf.org/doc/html/rfc9110
- RFC 1034 - Domain Names Concepts and Facilities: https://datatracker.ietf.org/doc/html/rfc1034
- RFC 1035 - Domain Names Implementation and Specification: https://datatracker.ietf.org/doc/html/rfc1035
- RFC 2131 - DHCP for IPv4: https://datatracker.ietf.org/doc/html/rfc2131
- RFC 8415 - DHCPv6: https://datatracker.ietf.org/doc/html/rfc8415
- RFC 1918 - Private IPv4 Address Space: https://datatracker.ietf.org/doc/html/rfc1918
- RFC 5737 - IPv4 Documentation Address Blocks: https://datatracker.ietf.org/doc/html/rfc5737
- RFC 6890 - Special-Purpose IP Address Registries: https://datatracker.ietf.org/doc/html/rfc6890

## Linux / Unix diagnostics

- Linux man-pages project: https://www.kernel.org/doc/man-pages/
- iproute2 documentation: https://wiki.linuxfoundation.org/networking/iproute2
- systemd systemctl manual: https://www.freedesktop.org/software/systemd/man/systemctl.html
- journalctl manual (man7 mirror): https://man7.org/linux/man-pages/man1/journalctl.1.html
- OpenSSH manual pages: https://www.openssh.com/manual.html
- tcpdump manual (man7 mirror): https://man7.org/linux/man-pages/man8/tcpdump.8.html

## Windows Server / PowerShell diagnostics

- PowerShell documentation: https://learn.microsoft.com/en-us/powershell/
- Test-NetConnection: https://learn.microsoft.com/en-us/powershell/module/nettcpip/test-netconnection
- Resolve-DnsName: https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname?view=windowsserver2025-ps
- Get-WinEvent: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent?view=powershell-7.6
- Windows Server DNS troubleshooting: https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-dns-guidance
- Windows DNS dynamic update troubleshooting: https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/troubleshooting-dns-dynamic-update-issues
- Active Directory replication concepts: https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/replication/active-directory-replication-concepts
- dcdiag reference: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/dcdiag
- AD replication troubleshooting with repadmin: https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/diagnose-replication-failures

## pfSense / firewall operations

- pfSense documentation home: https://docs.netgate.com/pfsense/en/latest/
- Troubleshooting firewall rules: https://docs.netgate.com/pfsense/en/latest/troubleshooting/firewall.html
- Troubleshooting NAT port forwards: https://docs.netgate.com/pfsense/en/latest/troubleshooting/nat-port-forwards.html
- Troubleshooting high availability: https://docs.netgate.com/pfsense/en/latest/troubleshooting/high-availability.html
- pfSense diagnostics menu guide: https://docs.netgate.com/pfsense/en/latest/menuguide/diagnostics.html
- Packet capturing in pfSense: https://docs.netgate.com/pfsense/en/latest/diagnostics/packetcapture/index.html

## Kubernetes / K3s

- Kubernetes troubleshooting overview: https://kubernetes.io/docs/tasks/debug/
- Debug Pods: https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/
- Debug Running Pods: https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/
- Debug Services: https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/
- Troubleshooting Clusters: https://kubernetes.io/docs/tasks/debug/debug-cluster/
- kubectl command reference: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands
- K3s documentation: https://docs.k3s.io/

## VMware / virtualization

- ESXi host not responding/disconnected troubleshooting: https://knowledge.broadcom.com/external/article/344682/troubleshooting-an-esxi-host-in-a-not-re.html
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

## v0.4.0 roadmap domain sources

### Database operations
- PostgreSQL monitoring statistics: https://www.postgresql.org/docs/current/monitoring-stats.html
- PostgreSQL monitoring database activity: https://www.postgresql.org/docs/current/monitoring.html
- MySQL SHOW PROCESSLIST: https://dev.mysql.com/doc/refman/8.2/en/show-processlist.html
- MongoDB current operations: https://www.mongodb.com/docs/manual/reference/method/db.currentop/

### Container runtime operations
- Docker container logs: https://docs.docker.com/reference/cli/docker/container/logs/
- Docker inspect: https://docs.docker.com/reference/cli/docker/inspect/
- Docker logging: https://docs.docker.com/engine/logging/

### Load balancers, reverse proxies, and web gateways
- NGINX load balancing: https://nginx.org/en/docs/http/load_balancing.html
- NGINX Admin Guide HTTP Load Balancer: https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/
- HAProxy configuration manual: https://www.haproxy.com/documentation/haproxy-configuration-manual/latest/
- Apache HTTP Server documentation: https://httpd.apache.org/

### PKI and certificates
- OpenSSL verify: https://docs.openssl.org/1.1.1/man1/verify/
- OpenSSL s_client connectivity testing: https://docs.pingidentity.com/solution-guides/standards_and_protocols_use_cases/htg_use_openssl_to_test_ssl_connectivity.html

### CI/CD operations
- GitHub Actions documentation: https://docs.github.com/actions
- GitLab CI/CD documentation: https://docs.gitlab.com/ci/

### Monitoring stacks
- Grafana Prometheus data source: https://grafana.com/docs/grafana/latest/datasources/prometheus/
- Grafana data sources: https://grafana.com/docs/grafana/latest/datasources/
- OpenSearch Grafana data source: https://grafana.com/docs/plugins/grafana-opensearch-datasource/latest/

### Message queues
- RabbitMQ monitoring: https://www.rabbitmq.com/docs/monitoring
- RabbitMQ command line tools: https://www.rabbitmq.com/docs/cli
- RabbitMQ clustering: https://www.rabbitmq.com/docs/clustering

### SSH and privileged access
- OpenSSH manual pages: https://www.openssh.com/manual.html
- sshd_config manual: https://man7.org/linux/man-pages/man5/sshd_config.5.html

### ITSM, disaster recovery, and audit evidence
- ServiceNow incident management: https://www.servicenow.com/docs/r/it-service-management/incident-management/c_IncidentManagement.html
- NIST SP 800-34 Rev. 1: https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final
- NIST SP 800-53 Rev. 5: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final

## Related references

- `references/command-execution-protocol.md`
- `references/risk-levels.md`
