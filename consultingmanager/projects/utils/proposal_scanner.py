"""
Proposal Scanner Utility
Scans project Business folders for .docx proposal files.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ProposalScanner:
    """Scanner for proposal files in project Business folders"""
    
    def __init__(self):
        self.proposal_patterns = [
            '*Proposal*.docx',
            '*proposal*.docx',
            '*PROPOSAL*.docx',
        ]
    
    def scan_project_business_folder(self, project_path: str) -> Dict[str, Any]:
        """
        Scan a project's Business folder for proposal files
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dict with scan results including proposal files found
        """
        result = {
            'proposal_files': [],
            'business_folder_path': None,
            'status': 'not_found',
            'error_message': '',
        }
        
        try:
            # Normalize incoming path
            normalized_path = (project_path or '').strip()
            project_dir = Path(normalized_path).expanduser()
            logger.info(f"Scanning project folder: [{normalized_path}] -> resolved=[{project_dir}] exists={project_dir.exists()} is_dir={project_dir.is_dir()}")
            
            if not project_dir.exists() or not project_dir.is_dir():
                result['status'] = 'error'
                result['error_message'] = f"Project folder does not exist or is not a directory: {normalized_path}"
                logger.error(result['error_message'])
                return result
            
            # Look for Business folder
            business_folder = None
            for subdir in project_dir.iterdir():
                if not subdir.is_dir():
                    continue
                
                subdir_name = subdir.name.lower()
                if subdir_name == 'business':
                    business_folder = subdir
                    break
            
            if not business_folder:
                result['status'] = 'not_found'
                result['error_message'] = "Business folder not found in project directory"
                logger.warning(f"Business folder not found in {project_dir}")
                return result
            
            result['business_folder_path'] = str(business_folder)
            
            # Search for proposal files
            proposal_files = []
            for pattern in self.proposal_patterns:
                proposal_files.extend(business_folder.glob(pattern))
            
            # Remove duplicates and sort
            proposal_files = sorted(set(proposal_files), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if proposal_files:
                result['proposal_files'] = [str(f) for f in proposal_files]
                result['status'] = 'found'
                logger.info(f"Found {len(proposal_files)} proposal file(s) in {business_folder}")
            else:
                result['status'] = 'not_found'
                result['error_message'] = "No proposal files found in Business folder"
                logger.info(f"No proposal files found in {business_folder}")
        
        except Exception as e:
            result['status'] = 'error'
            result['error_message'] = f"Error scanning project folder: {str(e)}"
            logger.error(f"Error scanning project folder {project_path}: {e}", exc_info=True)
        
        return result
    
    def get_project_path_from_metadata(self, project) -> Optional[str]:
        """
        Get project path from ProjectMetadata if available
        
        Args:
            project: Project instance
            
        Returns:
            Project path string or None
        """
        try:
            from files.models import ProjectMetadata
            metadata = project.metadata.first()
            if metadata and metadata.project_path:
                return metadata.project_path
        except Exception as e:
            logger.warning(f"Could not get project path from metadata: {e}")
        
        return None








