<#
.SYNOPSIS
Collects a narrow read-only Windows Server baseline.

.DESCRIPTION
Risk classification: SAFE_READ_ONLY + SENSITIVE_OUTPUT.
Collects basic computer, network, route, disk, service, and recent system error information.
Review and redact output before sharing. Output may include hostnames, IPs, service names, paths, and log messages.

.PARAMETER Help
Show quick usage information.

.PARAMETER LogHours
Number of hours to look back for recent system errors. Default: 6.

.PARAMETER MaxEvents
Maximum number of recent system error events to return. Default: 50.

.EXAMPLE
./windows-baseline-readonly.ps1 -Help

.EXAMPLE
./windows-baseline-readonly.ps1 -LogHours 2 -MaxEvents 25
#>
param(
    [switch]$Help,
    [ValidateRange(1,168)][int]$LogHours = 6,
    [ValidateRange(1,500)][int]$MaxEvents = 50
)

if ($Help) {
    @"
windows-baseline-readonly.ps1 - collect a narrow read-only Windows baseline

Usage:
  ./windows-baseline-readonly.ps1 [-LogHours N] [-MaxEvents N]
  ./windows-baseline-readonly.ps1 -Help

Risk classification:
  SAFE_READ_ONLY + SENSITIVE_OUTPUT

What it checks:
  computer info, IP configuration, IPv4 routes, disks, automatic services not
  running, and recent System log errors.

Operational notes:
  Run only on authorized systems. Redact hostnames, IPs, users, paths, service
  names, and event messages before sharing outside the operations context.
"@
    exit 0
}

$ErrorActionPreference = "Continue"
Write-Output "## computer"
Get-ComputerInfo | Select-Object CsName,WindowsProductName,OsVersion,OsArchitecture
Write-Output "## network"
Get-NetIPConfiguration
Write-Output "## routes"
Get-NetRoute -AddressFamily IPv4 | Select-Object DestinationPrefix,NextHop,InterfaceAlias,RouteMetric | Sort-Object DestinationPrefix
Write-Output "## disks"
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID,Size,FreeSpace
Write-Output "## services not running with automatic start"
Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -ne 'Running'} | Select-Object Name,Status,StartType
Write-Output "## recent system errors limited"
$startTime = (Get-Date).AddHours(-1 * $LogHours)
Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=$startTime} -MaxEvents $MaxEvents | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,Message
