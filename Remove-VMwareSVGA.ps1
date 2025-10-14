<#
.SYNOPSIS
    Removes VMware SVGA 3D device and its driver from Windows.

.DESCRIPTION
    This script identifies and removes VMware SVGA 3D graphics devices and their associated drivers.
    It requires administrative privileges to execute successfully.

    The script will:
    - Check for administrative privileges
    - Identify VMware SVGA devices
    - Remove the devices
    - Remove the driver package from the driver store
    - Provide detailed logging of all operations

.PARAMETER Force
    Skip confirmation prompts and force removal

.PARAMETER DriverOnly
    Only remove the driver package, leave devices intact

.EXAMPLE
    .\Remove-VMwareSVGA.ps1
    Removes VMware SVGA devices and drivers with confirmation prompts

.EXAMPLE
    .\Remove-VMwareSVGA.ps1 -Force
    Removes VMware SVGA devices and drivers without confirmation

.EXAMPLE
    .\Remove-VMwareSVGA.ps1 -DriverOnly
    Only removes the driver package from the driver store

.NOTES
    Author: Generated for VMware VM management
    Requires: PowerShell 5.1 or higher, Administrator privileges
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$DriverOnly
)

# Requires -RunAsAdministrator

#region Functions

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Info','Warning','Error','Success')]
        [string]$Level = 'Info'
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $colors = @{
        'Info' = 'White'
        'Warning' = 'Yellow'
        'Error' = 'Red'
        'Success' = 'Green'
    }

    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $colors[$Level]
}

function Test-Administrator {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-VMwareSVGADevices {
    Write-Log "Searching for VMware SVGA devices..." -Level Info

    # Search for VMware SVGA devices using multiple methods
    $devices = @()

    # Method 1: Using Get-PnpDevice
    try {
        $pnpDevices = Get-PnpDevice | Where-Object {
            $_.FriendlyName -like "*VMware SVGA*" -or
            $_.HardwareID -like "*VEN_15AD&DEV_0405*" -or
            $_.Class -eq "Display" -and $_.Manufacturer -like "*VMware*"
        }

        foreach ($device in $pnpDevices) {
            $devices += [PSCustomObject]@{
                FriendlyName = $device.FriendlyName
                InstanceId = $device.InstanceId
                DeviceId = $device.DeviceID
                Status = $device.Status
                Class = $device.Class
                Manufacturer = $device.Manufacturer
            }
        }
    }
    catch {
        Write-Log "Error searching for devices: $_" -Level Error
    }

    return $devices
}

function Get-VMwareSVGADrivers {
    Write-Log "Searching for VMware SVGA drivers in driver store..." -Level Info

    $drivers = @()

    try {
        # Get all OEM driver packages
        $allDrivers = Get-WindowsDriver -Online -All

        $vmwareDrivers = $allDrivers | Where-Object {
            $_.ProviderName -like "*VMware*" -and (
                $_.ClassName -eq "Display" -or
                $_.Driver -like "*vm3d*" -or
                $_.Driver -like "*vmware*svga*"
            )
        }

        foreach ($driver in $vmwareDrivers) {
            $drivers += [PSCustomObject]@{
                Driver = $driver.Driver
                OriginalFileName = $driver.OriginalFileName
                ClassName = $driver.ClassName
                ProviderName = $driver.ProviderName
                Version = $driver.Version
                Date = $driver.Date
            }
        }
    }
    catch {
        Write-Log "Error searching for drivers: $_" -Level Error
    }

    return $drivers
}

function Remove-VMwareSVGADevice {
    param(
        [Parameter(Mandatory=$true)]
        [object]$Device
    )

    Write-Log "Removing device: $($Device.FriendlyName)" -Level Info

    try {
        # Use pnputil to remove the device
        $deviceInstanceId = $Device.InstanceId

        # Remove device using Remove-PnpDevice
        $pnpDevice = Get-PnpDevice -InstanceId $deviceInstanceId

        if ($pnpDevice) {
            $pnpDevice | Disable-PnpDevice -Confirm:$false -ErrorAction Stop
            Write-Log "Device disabled successfully" -Level Success

            # Remove the device
            $result = pnputil /remove-device $deviceInstanceId 2>&1

            if ($LASTEXITCODE -eq 0) {
                Write-Log "Device removed successfully" -Level Success
                return $true
            }
            else {
                Write-Log "Failed to remove device. Output: $result" -Level Warning
                return $false
            }
        }
    }
    catch {
        Write-Log "Error removing device: $_" -Level Error
        return $false
    }
}

function Remove-VMwareSVGADriver {
    param(
        [Parameter(Mandatory=$true)]
        [object]$Driver
    )

    Write-Log "Removing driver package: $($Driver.Driver)" -Level Info

    try {
        # Use pnputil to remove the driver package
        $result = pnputil /delete-driver $($Driver.Driver) /uninstall /force 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Log "Driver package removed successfully" -Level Success
            return $true
        }
        else {
            Write-Log "Failed to remove driver package. Output: $result" -Level Warning
            return $false
        }
    }
    catch {
        Write-Log "Error removing driver: $_" -Level Error
        return $false
    }
}

#endregion

#region Main Script

Write-Log "=== VMware SVGA Device and Driver Removal Script ===" -Level Info
Write-Log "Script started" -Level Info

# Check for administrator privileges
if (-not (Test-Administrator)) {
    Write-Log "This script requires administrative privileges. Please run as Administrator." -Level Error
    exit 1
}

# Find VMware SVGA devices
$devices = Get-VMwareSVGADevices

if ($devices.Count -eq 0) {
    Write-Log "No VMware SVGA devices found" -Level Warning
}
else {
    Write-Log "Found $($devices.Count) VMware SVGA device(s)" -Level Info

    # Display found devices
    foreach ($device in $devices) {
        Write-Log "  - $($device.FriendlyName) (Status: $($device.Status))" -Level Info
    }
}

# Find VMware SVGA drivers
$drivers = Get-VMwareSVGADrivers

if ($drivers.Count -eq 0) {
    Write-Log "No VMware SVGA drivers found in driver store" -Level Warning
}
else {
    Write-Log "Found $($drivers.Count) VMware SVGA driver package(s)" -Level Info

    # Display found drivers
    foreach ($driver in $drivers) {
        Write-Log "  - $($driver.Driver) - $($driver.ClassName) (Version: $($driver.Version))" -Level Info
    }
}

# Exit if nothing found
if ($devices.Count -eq 0 -and $drivers.Count -eq 0) {
    Write-Log "Nothing to remove. Exiting." -Level Info
    exit 0
}

# Confirmation prompt
if (-not $Force) {
    Write-Host ""
    $confirmation = Read-Host "Do you want to proceed with removal? (Y/N)"
    if ($confirmation -ne 'Y' -and $confirmation -ne 'y') {
        Write-Log "Operation cancelled by user" -Level Warning
        exit 0
    }
}

Write-Host ""

# Remove devices (unless DriverOnly switch is used)
if (-not $DriverOnly) {
    if ($devices.Count -gt 0) {
        Write-Log "Starting device removal..." -Level Info

        $successCount = 0
        foreach ($device in $devices) {
            if (Remove-VMwareSVGADevice -Device $device) {
                $successCount++
            }
        }

        Write-Log "Device removal completed: $successCount of $($devices.Count) succeeded" -Level Info
    }
}
else {
    Write-Log "Skipping device removal (DriverOnly mode)" -Level Info
}

# Remove drivers
if ($drivers.Count -gt 0) {
    Write-Log "Starting driver removal..." -Level Info

    $successCount = 0
    foreach ($driver in $drivers) {
        if (Remove-VMwareSVGADriver -Driver $driver) {
            $successCount++
        }
    }

    Write-Log "Driver removal completed: $successCount of $($drivers.Count) succeeded" -Level Success
}

Write-Host ""
Write-Log "=== Script completed ===" -Level Success
Write-Log "A system restart is recommended to complete the removal process." -Level Warning

# Prompt for restart
if (-not $Force) {
    Write-Host ""
    $restart = Read-Host "Would you like to restart the computer now? (Y/N)"
    if ($restart -eq 'Y' -or $restart -eq 'y') {
        Write-Log "Restarting computer in 10 seconds..." -Level Warning
        shutdown /r /t 10 /c "Restarting after VMware SVGA driver removal"
    }
}

#endregion
