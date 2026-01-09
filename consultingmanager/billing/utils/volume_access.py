"""
Network Volume Access Utility

Provides utilities to diagnose and fix network volume access issues on macOS.
Common problem: Finder can see mounted volumes but Django/terminal processes cannot.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


def check_volume_accessible(volume_path: str) -> Dict[str, Any]:
    """
    Check if a volume path is accessible and provide diagnostic information.
    
    Args:
        volume_path: Path to check (e.g., '/Volumes/KAILUA PROJECTS/2023/...')
        
    Returns:
        Dictionary with diagnostic information:
        {
            'accessible': bool,
            'exists': bool,
            'is_dir': bool,
            'is_file': bool,
            'readable': bool,
            'volume_mount': str,  # e.g., '/Volumes/KAILUA PROJECTS'
            'volume_name': str,   # e.g., 'KAILUA PROJECTS'
            'mount_info': Dict,   # Information about the mount
            'error': str,         # Error message if any
        }
    """
    result = {
        'accessible': False,
        'exists': False,
        'is_dir': False,
        'is_file': False,
        'readable': False,
        'volume_mount': None,
        'volume_name': None,
        'mount_info': {},
        'error': None,
    }
    
    try:
        path = Path(volume_path).expanduser().resolve()
        result['exists'] = path.exists()
        result['is_dir'] = path.is_dir()
        result['is_file'] = path.is_file()
        result['readable'] = os.access(path, os.R_OK)
        result['accessible'] = result['exists'] and result['readable']
        
        # Extract volume information
        parts = path.parts
        if len(parts) > 0 and parts[0] == '/':
            if len(parts) > 1 and parts[1] == 'Volumes':
                result['volume_mount'] = f"/Volumes/{parts[2]}" if len(parts) > 2 else None
                result['volume_name'] = parts[2] if len(parts) > 2 else None
        
        # Get mount information
        if result['volume_mount']:
            result['mount_info'] = get_mount_info(result['volume_mount'])
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error checking volume access for {volume_path}: {e}")
    
    return result


def get_mount_info(mount_point: str) -> Dict[str, Any]:
    """
    Get information about a mounted volume using system commands.
    
    Args:
        mount_point: Mount point path (e.g., '/Volumes/KAILUA PROJECTS')
        
    Returns:
        Dictionary with mount information
    """
    info = {
        'mounted': False,
        'mount_type': None,
        'device': None,
        'options': None,
        'error': None,
    }
    
    try:
        # Use 'mount' command to check if volume is mounted
        result = subprocess.run(
            ['mount'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if mount_point in line:
                    info['mounted'] = True
                    parts = line.split()
                    if len(parts) >= 3:
                        info['device'] = parts[0]
                        info['mount_type'] = parts[4] if len(parts) > 4 else 'unknown'
                    break
        
        # Also check with 'df' command
        result_df = subprocess.run(
            ['df', mount_point],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result_df.returncode == 0:
            info['mounted'] = True
            lines = result_df.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) > 0:
                    info['device'] = parts[0]
            
    except subprocess.TimeoutExpired:
        info['error'] = 'Command timeout'
    except FileNotFoundError:
        info['error'] = 'mount/df commands not found'
    except Exception as e:
        info['error'] = str(e)
        logger.error(f"Error getting mount info for {mount_point}: {e}")
    
    return info


def list_mounted_volumes() -> List[Dict[str, Any]]:
    """
    List all currently mounted volumes in /Volumes.
    
    Returns:
        List of dictionaries with volume information
    """
    volumes = []
    volumes_dir = Path('/Volumes')
    
    try:
        if volumes_dir.exists():
            for item in volumes_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    vol_info = {
                        'name': item.name,
                        'path': str(item),
                        'exists': item.exists(),
                        'readable': os.access(item, os.R_OK),
                        'mount_info': get_mount_info(str(item)),
                    }
                    volumes.append(vol_info)
    except Exception as e:
        logger.error(f"Error listing mounted volumes: {e}")
    
    return volumes


def refresh_volume_access(volume_name: str) -> Dict[str, Any]:
    """
    Attempt to refresh access to a network volume.
    This can help when Finder can see the volume but terminal processes cannot.
    
    Args:
        volume_name: Name of the volume (e.g., 'KAILUA PROJECTS')
        
    Returns:
        Dictionary with operation results
    """
    result = {
        'success': False,
        'message': '',
        'error': None,
    }
    
    volume_path = f"/Volumes/{volume_name}"
    
    try:
        # Method 1: Try to stat the directory to "refresh" the mount
        if os.path.exists(volume_path):
            os.stat(volume_path)
            result['success'] = True
            result['message'] = f"Volume {volume_name} is accessible"
        else:
            result['message'] = f"Volume {volume_name} not found at {volume_path}"
            result['error'] = 'Volume not found'
            
            # Try to list /Volumes to see if it appears
            volumes = list_mounted_volumes()
            volume_names = [v['name'] for v in volumes]
            if volume_name in volume_names:
                result['message'] = f"Volume {volume_name} found but may not be accessible"
            else:
                result['message'] = f"Volume {volume_name} not in mounted volumes: {volume_names}"
                
    except PermissionError as e:
        result['error'] = f"Permission denied: {e}"
        result['message'] = f"Permission denied accessing {volume_name}"
    except OSError as e:
        result['error'] = str(e)
        result['message'] = f"OS error accessing {volume_name}: {e}"
    except Exception as e:
        result['error'] = str(e)
        result['message'] = f"Unexpected error: {e}"
        logger.error(f"Error refreshing volume access for {volume_name}: {e}")
    
    return result


def attempt_volume_reconnection(volume_name: str) -> Dict[str, Any]:
    """
    Attempt various methods to reconnect to a network volume.
    This is a helper function that tries multiple approaches.
    
    Args:
        volume_name: Name of the volume
        
    Returns:
        Dictionary with results from all attempts
    """
    results = {
        'volume_name': volume_name,
        'methods_tried': [],
        'success': False,
        'best_message': '',
    }
    
    # Method 1: Refresh access
    refresh_result = refresh_volume_access(volume_name)
    results['methods_tried'].append({
        'method': 'refresh_access',
        'success': refresh_result['success'],
        'message': refresh_result['message'],
    })
    
    if refresh_result['success']:
        results['success'] = True
        results['best_message'] = refresh_result['message']
        return results
    
    # Method 2: Check mount status
    volume_path = f"/Volumes/{volume_name}"
    mount_info = get_mount_info(volume_path)
    results['methods_tried'].append({
        'method': 'check_mount',
        'mounted': mount_info['mounted'],
        'message': f"Mount status: {mount_info}",
    })
    
    if not mount_info['mounted']:
        results['best_message'] = f"Volume {volume_name} is not mounted. Please mount it via Finder or System Preferences."
        return results
    
    # Method 3: Try accessing parent directory
    try:
        volumes_dir = Path('/Volumes')
        if volumes_dir.exists():
            os.stat(volumes_dir)
            results['methods_tried'].append({
                'method': 'check_volumes_dir',
                'success': True,
                'message': '/Volumes directory is accessible',
            })
    except Exception as e:
        results['methods_tried'].append({
            'method': 'check_volumes_dir',
            'success': False,
            'message': f'/Volumes directory error: {e}',
        })
    
    results['best_message'] = f"Volume {volume_name} appears mounted but may not be accessible. Try disconnecting and reconnecting the volume."
    return results


def diagnose_file_access(file_path: str) -> Dict[str, Any]:
    """
    Comprehensive diagnosis of file access issues.
    
    Args:
        file_path: Full path to the file
        
    Returns:
        Dictionary with comprehensive diagnostic information
    """
    diagnosis = {
        'file_path': file_path,
        'file_check': check_volume_accessible(file_path),
        'parent_dir_check': None,
        'volume_check': None,
        'suggestions': [],
    }
    
    path = Path(file_path)
    
    # Check parent directory
    if path.parent.exists():
        diagnosis['parent_dir_check'] = check_volume_accessible(str(path.parent))
    
    # Check volume mount
    file_check = diagnosis['file_check']
    if file_check.get('volume_mount'):
        diagnosis['volume_check'] = check_volume_accessible(file_check['volume_mount'])
        mount_info = file_check.get('mount_info', {})
        
        if not mount_info.get('mounted'):
            diagnosis['suggestions'].append(
                f"Volume {file_check.get('volume_name')} does not appear to be mounted. "
                "Try disconnecting and reconnecting the volume in Finder."
            )
        
        if not file_check.get('readable'):
            diagnosis['suggestions'].append(
                f"Volume is mounted but not readable. Check file permissions and "
                "ensure the Django process has access to the volume."
            )
    
    if not diagnosis['file_check'].get('exists'):
        diagnosis['suggestions'].append(
            f"File does not exist at {file_path}. Verify the path is correct."
        )
    
    if diagnosis['file_check'].get('exists') and not diagnosis['file_check'].get('readable'):
        diagnosis['suggestions'].append(
            "File exists but is not readable. Check file permissions."
        )
    
    if not diagnosis['suggestions']:
        diagnosis['suggestions'].append(
            "File appears to be accessible. If errors persist, try refreshing the volume connection."
        )
    
    return diagnosis






