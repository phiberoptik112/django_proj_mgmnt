# Network Volume Access Troubleshooting Guide

## Problem

Django cannot access files on network volumes (e.g., `/Volumes/KAILUA PROJECTS/...`) even though Finder can see and access them. This is a common issue on macOS when network volumes are mounted but not accessible to terminal/Django processes.

## Solutions

### Option 1: Use the Web Interface (Recommended)

When viewing a PIF scan result page, if the file is inaccessible, you'll see a warning alert with a **"Refresh Volume Access"** button. Click this button to attempt to refresh the volume connection.

**Steps:**
1. Navigate to the PIF scan result page that's showing the error
2. Look for the yellow warning alert at the top
3. Click the **"Refresh Volume Access"** button
4. The system will attempt to refresh the volume connection
5. Reload the page to see if the file is now accessible

### Option 2: Use the Management Command

Use the Django management command to diagnose and fix volume access issues:

#### List All Mounted Volumes
```bash
cd consultingmanager
python manage.py check_volume_access --list
```

#### Check Access to a Specific File
```bash
python manage.py check_volume_access --file "/Volumes/KAILUA PROJECTS/2023/P23-033 HIANG Bldg 705/Business/PIFX 23-033.xlsx"
```

#### Check Access to a Volume
```bash
python manage.py check_volume_access --volume "KAILUA PROJECTS"
```

#### Refresh Volume Access
```bash
python manage.py check_volume_access --refresh "KAILUA PROJECTS"
```

#### Run Full Diagnosis on a File
```bash
python manage.py check_volume_access --diagnose "/Volumes/KAILUA PROJECTS/2023/P23-033 HIANG Bldg 705/Business/PIFX 23-033.xlsx"
```

#### Attempt Volume Reconnection
```bash
python manage.py check_volume_access --reconnect "KAILUA PROJECTS"
```

### Option 3: Manual Finder Refresh (Most Reliable)

If automated methods don't work, manually refresh the volume in Finder:

1. **Disconnect the Volume:**
   - Open Finder
   - Right-click on the volume (e.g., "KAILUA PROJECTS")
   - Select "Eject" or drag it to the Trash

2. **Reconnect the Volume:**
   - Open Finder
   - Press `Cmd+K` (or Go → Connect to Server)
   - Enter the server address
   - Wait for the volume to mount

3. **Verify Access:**
   - Try accessing the file in Finder
   - Run the diagnosis command to verify Django can access it:
     ```bash
     python manage.py check_volume_access --file "/path/to/file.xlsx"
     ```

### Option 4: Check System-Level Mount Status

You can verify the volume is properly mounted using terminal commands:

```bash
# List all mounted volumes
mount | grep Volumes

# Check if a specific volume is mounted
df -h | grep "KAILUA PROJECTS"

# Check volume permissions
ls -la /Volumes/
```

## Understanding the Diagnostics

When you run diagnostics, you'll see information about:

- **File Exists**: Whether the file path exists
- **Readable**: Whether the file can be read
- **Volume Mounted**: Whether the volume appears in the system mount table
- **Mount Device**: The underlying device/network path
- **Suggestions**: Specific steps to resolve the issue

## Common Causes

1. **Volume Not Properly Mounted**: The volume appears in Finder but isn't in the system mount table
2. **Permission Issues**: The Django process doesn't have read permissions
3. **Network Timeout**: The network connection has timed out
4. **Volume Disconnected**: The volume was disconnected but Finder still shows it
5. **Mount Point Issues**: The mount point exists but the volume isn't actually accessible

## Technical Details

The system uses the following utilities to diagnose and fix issues:

- **`volume_access.py`**: Core utility module for volume diagnostics
- **`check_volume_accessible()`**: Checks if a file path is accessible
- **`diagnose_file_access()`**: Provides comprehensive diagnostics
- **`refresh_volume_access()`**: Attempts to refresh volume connections
- **`attempt_volume_reconnection()`**: Tries multiple methods to reconnect

All diagnostics are logged to Django's logging system, so check your logs for detailed error messages.

## Getting Help

If none of these solutions work:

1. Check Django logs for detailed error messages
2. Verify the volume is accessible in Terminal:
   ```bash
   ls /Volumes/KAILUA\ PROJECTS/
   ```
3. Check system logs for mount-related errors
4. Ensure the Django server process has the same user permissions as your Finder session

