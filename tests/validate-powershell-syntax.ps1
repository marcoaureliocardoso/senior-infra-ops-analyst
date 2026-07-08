$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "../skills/command-driven-operations/scripts/windows-baseline-readonly.ps1"
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$errors) | Out-Null
if ($errors -and $errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_.Message }
    exit 1
}
Write-Output "PowerShell syntax OK: $scriptPath"
