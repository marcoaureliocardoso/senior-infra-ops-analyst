# SAFE_READ_ONLY + SENSITIVE_OUTPUT: collect a narrow Windows baseline.
# Review and redact output before sharing.
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
Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddHours(-6)} -MaxEvents 50 | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,Message
