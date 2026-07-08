# VMware / ESXi Operations

Use for ESXi hosts, VMs, datastores, snapshots, networking, and hypervisor health. Commands vary by version and privilege. Prefer vCenter/GUI/API for managed environments when available.

## Safety rules

- Do not power off/reset VMs, remove snapshots, enter maintenance mode, rescan storage, or change networking without approval.
- Confirm the host, VM, datastore, and cluster before any action.
- Snapshot deletion/consolidation can be high impact on storage and performance.
- Preserve evidence before remediation.

## 1. Safe ESXi identification

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `hostname` | Host identity | Confirm correct ESXi host. |
| SAFE_READ_ONLY | `esxcli system version get` | ESXi version/build | Useful for lifecycle/compatibility. |
| SAFE_READ_ONLY | `esxcli hardware platform get` | Hardware model | Hardware lifecycle and support clues. |
| SAFE_READ_ONLY | `uptime` | Host uptime/load clue | Recent reboot may explain VM impact. |

## 2. VM inventory and state

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `vim-cmd vmsvc/getallvms` | VM IDs/inventory | Get VMID before read-only VM checks. |
| SAFE_READ_ONLY | `vim-cmd vmsvc/power.getstate <vmid>` | VM power state | Powered off/suspended vs running. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `vim-cmd vmsvc/get.summary <vmid>` | VM summary | Tools status, config, runtime clues. |
| DISRUPTIVE_CHANGE | `vim-cmd vmsvc/power.reset <vmid>` | Hard reset VM | Requires approval; can cause data loss. |
| DISRUPTIVE_CHANGE | `vim-cmd vmsvc/power.off <vmid>` | Power off VM | Requires approval; user impact. |

## 3. Datastore and storage

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `esxcli storage filesystem list` | Datastore usage/mount | Full or unmounted datastore explains VM issues. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `esxcli storage core device list \| head -80` | Device visibility | Missing/degraded storage path. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `esxcli storage core path list \| head -120` | Storage paths | Dead paths indicate SAN/iSCSI/FC issues. |
| DISRUPTIVE_CHANGE | Storage rescan/remount | Storage state | Requires approval and maintenance awareness. |

## 4. Networking

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `esxcli network nic list` | Physical NICs | Down NIC or wrong speed impacts VMs. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `esxcli network vswitch standard list` | vSwitch state | Missing portgroup/vSwitch mismatch. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `esxcli network ip interface ipv4 get` | VMkernel IPs | Management/vMotion/storage network clue. |
| SAFE_READ_ONLY | `esxcli network ip route ipv4 list` | Routing | Management/storage path issues. |
| DISRUPTIVE_CHANGE | vSwitch/portgroup/NIC changes | Network path | Requires approval and rollback path. |

## 5. Snapshots

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `vim-cmd vmsvc/snapshot.get <vmid>` | Snapshot tree | Old/large snapshots are risk. |
| DESTRUCTIVE | Snapshot remove/delete/consolidate | Disk chain change | Requires approval, backup, and storage headroom. |

## 6. Diagnostic order for VM down/slowness

1. Confirm host identity and VMID.
2. Check VM power state and summary.
3. Check datastore capacity/mount.
4. Check host NIC/vSwitch state.
5. Check storage paths.
6. Check recent host/VM events in vCenter if available.
7. Present remediation options requiring approval.


## Sensitivity and load notes

VM inventories, datastore names, network names, and snapshot trees reveal private topology and business context. Summarize relevant findings and redact identifiers when needed. Avoid repeated broad ESXi queries during host instability.
