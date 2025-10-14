# windows_scripts
Scripts for Windows Administration

## Scripts

### Remove-VMwareSVGA.ps1

A PowerShell script to remove VMware SVGA 3D graphics devices and their associated drivers from Windows systems, particularly useful for VMware hosted virtual machines.

#### Purpose

This script safely removes VMware SVGA display adapters and cleans up their driver packages from the Windows driver store. This is useful when:
- Transitioning from VMware graphics drivers to other display solutions
- Troubleshooting graphics issues in VMware VMs
- Cleaning up orphaned or problematic VMware display drivers
- Preparing systems for driver updates or replacements

#### Requirements

- Windows PowerShell 5.1 or higher
- Administrator privileges
- Windows 10/11 or Windows Server 2016+

#### Usage

**Basic usage with confirmation prompts:**
```powershell
.\Remove-VMwareSVGA.ps1
```

**Force removal without prompts:**
```powershell
.\Remove-VMwareSVGA.ps1 -Force
```

**Remove only driver packages (leave devices intact):**
```powershell
.\Remove-VMwareSVGA.ps1 -DriverOnly
```

#### Features

- **Device Detection**: Automatically identifies VMware SVGA devices using multiple detection methods
- **Driver Store Cleanup**: Removes driver packages from the Windows driver store
- **Safety Checks**:
  - Requires administrator privileges
  - Confirmation prompts before removal (unless `-Force` is used)
  - Detailed logging with color-coded output
- **Flexible Options**:
  - `-Force` parameter to skip confirmations
  - `-DriverOnly` parameter to preserve devices while removing drivers
- **Comprehensive Logging**: Real-time status updates with timestamps and severity levels

#### What the Script Does

1. Verifies administrative privileges
2. Scans for VMware SVGA devices and drivers
3. Displays all detected items
4. Requests user confirmation (unless `-Force` is specified)
5. Disables and removes devices from the system
6. Removes driver packages using `pnputil`
7. Recommends system restart to complete removal
8. Optionally restarts the system

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `-Force` | Switch | No | Skip all confirmation prompts and force removal |
| `-DriverOnly` | Switch | No | Only remove driver packages, leave devices intact |

#### Output Example

```
[2025-10-13 14:30:45] [Info] === VMware SVGA Device and Driver Removal Script ===
[2025-10-13 14:30:45] [Info] Script started
[2025-10-13 14:30:45] [Info] Searching for VMware SVGA devices...
[2025-10-13 14:30:46] [Info] Found 1 VMware SVGA device(s)
[2025-10-13 14:30:46] [Info]   - VMware SVGA 3D (Status: OK)
[2025-10-13 14:30:46] [Info] Searching for VMware SVGA drivers in driver store...
[2025-10-13 14:30:47] [Info] Found 1 VMware SVGA driver package(s)
[2025-10-13 14:30:47] [Info]   - oem12.inf - Display (Version: 8.17.2.14)
[2025-10-13 14:30:50] [Success] Device removed successfully
[2025-10-13 14:30:51] [Success] Driver package removed successfully
[2025-10-13 14:30:51] [Success] === Script completed ===
```

#### Important Notes

- **System Restart**: A restart is recommended after removal to complete the process
- **Backup**: Consider creating a system restore point before running
- **Graphics Impact**: Removing the VMware SVGA driver may affect display functionality until an alternative driver is installed
- **Reversibility**: Driver reinstallation may require VMware Tools reinstallation or manual driver installation

#### Troubleshooting

**Script fails with "Access Denied":**
- Ensure you're running PowerShell as Administrator
- Right-click PowerShell and select "Run as Administrator"

**No devices found:**
- Verify you're running on a VMware virtual machine
- Check Device Manager to confirm VMware SVGA devices are present

**Driver removal fails:**
- Some drivers may be in use; ensure no graphics-intensive applications are running
- Try running in Safe Mode for stubborn drivers

**Display issues after removal:**
- Install alternative graphics drivers (e.g., Microsoft Basic Display Adapter will be used by default)
- Reinstall VMware Tools if needed
