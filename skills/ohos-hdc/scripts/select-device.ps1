#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Interactive HDC device selector. Returns selected device ID.

.PARAMETER Hint
    Filter devices by partial match (USB, TCP, IP, serial prefix)

.PARAMETER First
    Auto-select first available device

.PARAMETER SetEnv
    Set $env:HDC_DEVICE after selection

.EXAMPLE
    # Interactive selection
    $DEVICE_ID = .\select-device.ps1
    
    # Auto-select first USB device
    $DEVICE_ID = .\select-device.ps1 -Hint "USB" -First
    
    # Set environment variable
    .\select-device.ps1 -SetEnv
    hdc -t $env:HDC_DEVICE shell ls

.OUTPUTS
    Device ID string
#>

param(
    [string]$Hint = "",
    [switch]$First,
    [switch]$SetEnv
)

$ErrorActionPreference = "Stop"

# Get device list
$raw = hdc list targets -v 2>&1
if ($raw -match "Empty" -or -not $raw) {
    Write-Error "No devices connected. Check USB connection and run 'hdc kill -r'"
    exit 1
}

# Parse devices
$devices = @()
$raw -split "`n" | Where-Object { $_ -match '\S' } | ForEach-Object {
    $parts = $_ -split '\s+' | Where-Object { $_ }
    if ($parts.Count -ge 2) {
        $devices += [PSCustomObject]@{
            Id     = $parts[0]
            State  = $parts[1]
            Type   = if ($parts.Count -ge 3) { $parts[2] } else { "Unknown" }
            Raw    = $_
        }
    }
}

if ($devices.Count -eq 0) {
    Write-Error "Failed to parse device list"
    exit 1
}

# Apply hint filter
if ($Hint) {
    $filtered = $devices | Where-Object { $_.Raw -match $Hint }
    if ($filtered) {
        $devices = @($filtered)
    } else {
        Write-Warning "No devices match hint '$Hint', showing all"
    }
}

# Select device
$selected = $null

if ($devices.Count -eq 1 -or $First) {
    $selected = $devices[0]
    if (-not $First -and $devices.Count -eq 1) {
        Write-Host "Single device: $($selected.Id) [$($selected.Type)]" -ForegroundColor Cyan
    }
} else {
    # Interactive selection
    Write-Host "`nConnected devices:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $devices.Count; $i++) {
        $d = $devices[$i]
        $typeColor = switch ($d.Type) {
            "USB" { "Green" }
            "TCP" { "Yellow" }
            default { "Gray" }
        }
        Write-Host "  [$i] " -NoNewline
        Write-Host "$($d.Id)" -ForegroundColor White -NoNewline
        Write-Host " ($($d.State)) " -ForegroundColor Gray -NoNewline
        Write-Host "[$($d.Type)]" -ForegroundColor $typeColor
    }
    
    $choice = Read-Host "`nSelect device [0-$($devices.Count - 1)]"
    
    if ($choice -match '^\d+$' -and [int]$choice -lt $devices.Count) {
        $selected = $devices[[int]$choice]
    } else {
        Write-Error "Invalid selection"
        exit 1
    }
}

# Verify device is responsive
Write-Host "Verifying $($selected.Id)..." -ForegroundColor Gray -NoNewline
try {
    $check = hdc -t $selected.Id shell "echo OK" 2>&1
    if ($check -eq "OK") {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " Warning: Device may not be fully responsive" -ForegroundColor Yellow
    }
} catch {
    Write-Host " Warning: Could not verify" -ForegroundColor Yellow
}

# Set environment variable if requested
if ($SetEnv) {
    $env:HDC_DEVICE = $selected.Id
    Write-Host "`n`$env:HDC_DEVICE = '$($selected.Id)'" -ForegroundColor Green
    Write-Host "Use: hdc -t `$env:HDC_DEVICE <command>" -ForegroundColor Gray
}

# Return device ID
return $selected.Id
