"""
PIF Scanner Utility
Scans project directories for PIF (Project Information Form) files and extracts metadata.
"""

import os
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

class PIFScanner:
    """Scanner for PIF files in project directories"""
    
    def __init__(self):
        self.pif_patterns = [
            r'PIF.*\.xlsx',
            r'PIFX.*\.xlsx',
            r'Project.*Information.*Form.*\.xlsx',
            r'PIF.*\.xls',
            r'PIFX.*\.xls',
        ]
    
    def scan_year_folder(self, year_folder_path: str) -> List[Dict[str, Any]]:
        """
        Scan a year folder for PIF files
        
        Args:
            year_folder_path: Path to the year folder (e.g., /Volumes/KAILUA PROJECTS/2023)
            
        Returns:
            List of scan results
        """
        results = []
        year_path = Path(year_folder_path)
        
        if not year_path.exists():
            logger.error(f"Year folder does not exist: {year_folder_path}")
            return results
        
        # Scan each project directory in the year folder
        for project_dir in year_path.iterdir():
            if not project_dir.is_dir():
                continue
            
            # Skip non-project directories
            if not self._is_project_directory(project_dir.name):
                continue
            
            # Scan the project directory
            project_results = self._scan_project_directory(project_dir)
            results.extend(project_results)
        
        return results
    
    def _is_project_directory(self, dir_name: str) -> bool:
        """Check if a directory name looks like a project directory"""
        # Look for project number patterns like P23-001, 23-001, P24-123, 24-123, etc.
        project_pattern = r'^P?\d{2}-\d{3}'
        return bool(re.match(project_pattern, dir_name))
    
    def _scan_project_directory(self, project_dir: Path) -> List[Dict[str, Any]]:
        """Scan a single project directory for PIF files"""
        results = []
        
        # Look for Business and Documents subdirectories
        for subdir in project_dir.iterdir():
            if not subdir.is_dir():
                continue
            
            subdir_name = subdir.name.lower()
            if subdir_name in ['business', 'documents']:
                result = self._scan_subdirectory(subdir, subdir.name)
                if result:
                    results.append(result)
        
        return results
    
    def _scan_subdirectory(self, subdir: Path, folder_kind: str) -> Optional[Dict[str, Any]]:
        """Scan a subdirectory (Business/Documents) for PIF files"""
        result = {
            'container_dir': str(subdir),
            'folder_kind': folder_kind,
            'status': 'skipped',
            'reason': 'no_pif_found',
            'pif_file': '',
            'files_count': 0,
            'rows': None,
        }
        
        # Count files in directory
        files = list(subdir.glob('*'))
        result['files_count'] = len([f for f in files if f.is_file()])
        
        # Look for PIF files
        pif_files = []
        for pattern in self.pif_patterns:
            pif_files.extend(subdir.glob(pattern))
        
        if pif_files:
            # Use the first PIF file found
            pif_file = pif_files[0]
            result['pif_file'] = str(pif_file)
            result['status'] = 'ingested'
            result['reason'] = 'ok'
            
            # Try to read the Excel file and count rows
            try:
                df = pd.read_excel(pif_file, engine='openpyxl')
                result['rows'] = len(df)
            except Exception as e:
                result['status'] = 'error'
                result['reason'] = f"Error reading Excel file: {str(e)}"
                logger.error(f"Error reading PIF file {pif_file}: {e}")
        
        return result
    
    def scan_and_export_csv(self, year_folder_path: str, output_csv_path: str) -> Dict[str, Any]:
        """
        Scan a year folder and export results to CSV
        
        Args:
            year_folder_path: Path to the year folder
            output_csv_path: Path to save the CSV file
            
        Returns:
            Summary statistics
        """
        results = self.scan_year_folder(year_folder_path)
        
        if results:
            # Convert to DataFrame and save
            df = pd.DataFrame(results)
            df.to_csv(output_csv_path, index=False)
            
            # Calculate statistics
            stats = {
                'total_scanned': len(results),
                'ingested': len([r for r in results if r['status'] == 'ingested']),
                'skipped': len([r for r in results if r['status'] == 'skipped']),
                'errors': len([r for r in results if r['status'] == 'error']),
                'output_file': output_csv_path,
            }
        else:
            stats = {
                'total_scanned': 0,
                'ingested': 0,
                'skipped': 0,
                'errors': 0,
                'output_file': output_csv_path,
            }
        
        return stats
    
    def scan_multiple_years(self, year_folders: List[str], output_dir: str) -> Dict[str, Any]:
        """
        Scan multiple year folders and export results
        
        Args:
            year_folders: List of year folder paths
            output_dir: Directory to save CSV files
            
        Returns:
            Summary statistics
        """
        all_results = []
        output_files = []
        
        for year_folder in year_folders:
            year_name = Path(year_folder).name
            output_file = os.path.join(output_dir, f'pif_scan_{year_name}.csv')
            
            results = self.scan_year_folder(year_folder)
            all_results.extend(results)
            
            if results:
                df = pd.DataFrame(results)
                df.to_csv(output_file, index=False)
                output_files.append(output_file)
        
        # Create combined CSV
        if all_results:
            combined_file = os.path.join(output_dir, 'pif_scan_combined.csv')
            combined_df = pd.DataFrame(all_results)
            combined_df.to_csv(combined_file, index=False)
            output_files.append(combined_file)
        
        # Calculate overall statistics
        stats = {
            'total_scanned': len(all_results),
            'ingested': len([r for r in all_results if r['status'] == 'ingested']),
            'skipped': len([r for r in all_results if r['status'] == 'skipped']),
            'errors': len([r for r in all_results if r['status'] == 'error']),
            'output_files': output_files,
        }
        
        return stats
