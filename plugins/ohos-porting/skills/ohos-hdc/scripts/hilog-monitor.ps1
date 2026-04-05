#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Monitor and filter KaihongOS device logs via HDC hilog.

.PARAMETER DeviceId
    Target device ID (REQUIRED). Get via: hdc list targets

.PARAMETER Filter
    Regex pattern to filter logs

.PARAMETER Level
    Log level filter: D(ebug), I(nfo), W(arn), E(rror), F(atal)

.PARAMETER Tag
    Filter by specific tag

.PARAMETER Output
    Save logs to file

.PARAMETER Duration
    Stop after N seconds (0 = indefinite)

.PARAMETER Clear
    Clear device logs before starting

.EXAMPLE
    # List devices first
    hdc list targets -v
    
    # Monitor with filter
    .\hilog-monitor.ps1 -DeviceId "7001005..." -Filter "dsoftbus|rmw" -Level E
    
    # Save to file for 60 seconds
    .\hilog-monitor.ps1 -DeviceId "7001005..." -Tag "ROS2" -Output .\ros2.log -Duration 60 -Clear
#>

param(
    [Parameter(Mandatory=$true, HelpMessage="Device ID from 'hdc list targets'")]
    [string]$DeviceId,
    
    [string]$Filter = "",
    
    [ValidateSet("", "D", "I", "W", "E", "F")]
    [string]$Level = "",
    
    [string]$Tag = "",
    [string]$Output = "",
    [int]$Duration = 0,
    [switch]$Clear
)

$ErrorActionPreference = "Stop"

# Verify device
Write-Host "[*] Connecting to $DeviceId..." -ForegroundColor Cyan
try {
    $check = hdc -t $DeviceId shell "echo OK" 2>&1
    if ($check -ne "OK") {
        throw "Device not responding"
    }
} catch {
    Write-Error "Cannot connect to device: $DeviceId"
    exit 1
}

# Clear logs if requested
if ($Clear) {
    Write-Host "[*] Clearing device logs..." -ForegroundColor Yellow
    hdc -t $DeviceId shell "hilog -r" 2>&1 | Out-Null
}

# Build filter pattern
$patterns = @()
if ($Filter) { $patterns += $Filter }
if ($Level) { $patterns += "^\d{2}-\d{2}.*\s$Level/" }
if ($Tag) { $patterns += "\s$Tag\s|\[$Tag\]" }

$combinedPattern = if ($patterns.Count -gt 0) {
    "(" + ($patterns -join "|") + ")"
} else {
    "."  # Match all
}

# Display config
Write-Host "[*] Starting hilog monitor" -ForegroundColor Cyan
Write-Host "    Device:   $DeviceId" -ForegroundColor Gray
Write-Host "    Filter:   $combinedPattern" -ForegroundColor Gray
if ($Output) {
    Write-Host "    Output:   $Output" -ForegroundColor Gray
    # Ensure output directory exists
    $outDir = Split-Path $Output -Parent
    if ($outDir -and -not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }
}
if ($Duration -gt 0) {
    Write-Host "    Duration: ${Duration}s" -ForegroundColor Gray
}
Write-Host "    Press Ctrl+C to stop`n" -ForegroundColor Yellow

$startTime = Get-Date
$lineCount = 0
$matchCount = 0

try {
    hdc -t $DeviceId hilog 2>&1 | ForEach-Object {
        $line = $_
        $lineCount++
        
        # Check duration limit
        if ($Duration -gt 0) {
            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            if ($elapsed -ge $Duration) {
                throw "DurationReached"
            }
        }
        
        # Apply filter
        if ($line -match $combinedPattern) {
            $matchCount++
            
            # Colorize by level
            $color = switch -Regex ($line) {
                '\sF/' { 'Magenta' }
                '\sE/' { 'Red' }
                '\sW/' { 'Yellow' }
                '\sI/' { 'White' }
                '\sD/' { 'DarkGray' }
                default { 'Gray' }
            }
            
            Write-Host $line -ForegroundColor $color
            
            # Save to file
            if ($Output) {
                $line | Out-File -FilePath $Output -Append -Encoding UTF8
            }
        }
    }
} catch {
    if ($_.Exception.Message -ne "DurationReached") {
        # Ctrl+C or real error
    }
}

# Summary
$elapsed = ((Get-Date) - $startTime).TotalSeconds
Write-Host "`n[+] Processed $lineCount lines, matched $matchCount ($($elapsed.ToString('F1'))s)" -ForegroundColor Green
if ($Output) {
    Write-Host "    Saved to: $Output" -ForegroundColor Gray
}
