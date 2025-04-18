import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import magic
from django.conf import settings
from django.utils import timezone

from ..models import Project, ProjectFolder, FileMetadata, ProjectAnalysis

class FileProcessor:
    """Service class for processing files and extracting metadata"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
    def process_project(self, project_code: str) -> Project:
        """Process a project directory and store its metadata"""
        project_path = self._find_project_path(project_code)
        if not project_path:
            raise ValueError(f"Project {project_code} not found")
            
        # Create or get project
        year = int(project_code.split('-')[0])
        project, _ = Project.objects.get_or_create(
            project_code=project_code,
            defaults={
                'name': project_path.name,
                'year': year
            }
        )
        
        # Process folders and files
        self._process_folders(project, project_path)
        
        return project
        
    def _find_project_path(self, project_code: str) -> Optional[Path]:
        """Find the full path to a project directory"""
        for year_dir in self.base_path.iterdir():
            if not year_dir.is_dir():
                continue
                
            project_dir = year_dir / project_code
            if project_dir.exists() and project_dir.is_dir():
                return project_dir
                
        return None
        
    def _process_folders(self, project: Project, project_path: Path):
        """Process all folders in a project"""
        for root, dirs, files in os.walk(project_path):
            root_path = Path(root)
            relative_path = root_path.relative_to(project_path)
            
            # Create or get folder
            folder = self._get_or_create_folder(project, relative_path)
            
            # Process files in this folder
            for file in files:
                file_path = root_path / file
                self._process_file(project, folder, file_path)
                
    def _get_or_create_folder(self, project: Project, relative_path: Path) -> ProjectFolder:
        """Create or get a ProjectFolder instance"""
        folder_name = relative_path.name
        folder_type = self._determine_folder_type(folder_name)
        
        # Get or create parent folder if needed
        parent_folder = None
        if relative_path.parent != Path('.'):
            parent_folder = self._get_or_create_folder(project, relative_path.parent)
            
        folder, _ = ProjectFolder.objects.get_or_create(
            project=project,
            relative_path=str(relative_path),
            defaults={
                'name': folder_name,
                'folder_type': folder_type,
                'parent_folder': parent_folder
            }
        )
        
        return folder
        
    def _determine_folder_type(self, folder_name: str) -> str:
        """Determine the type of a folder based on its name"""
        folder_name = folder_name.upper()
        
        if 'BUSINESS' in folder_name:
            return 'BUSINESS'
        elif 'TECHNICAL' in folder_name:
            return 'TECHNICAL'
        elif 'ADMIN' in folder_name:
            return 'ADMIN'
        else:
            return 'OTHER'
            
    def _process_file(self, project: Project, folder: ProjectFolder, file_path: Path):
        """Process a single file and store its metadata"""
        stat = file_path.stat()
        
        # Calculate file hashes
        hashes = self._calculate_file_hashes(file_path)
        
        # Get MIME type
        mime_type = magic.from_file(str(file_path), mime=True)
        
        # Create timezone-aware datetimes
        created_time = timezone.make_aware(datetime.fromtimestamp(stat.st_ctime))
        modified_time = timezone.make_aware(datetime.fromtimestamp(stat.st_mtime))
        
        # Create or update file metadata
        FileMetadata.objects.update_or_create(
            project=project,
            folder=folder,
            full_path=str(file_path),
            defaults={
                'filename': file_path.name,
                'file_type': file_path.suffix.lower(),
                'size_bytes': stat.st_size,
                'created_time': created_time,
                'modified_time': modified_time,
                'mime_type': mime_type,
                'md5_hash': hashes['md5'],
                'sha1_hash': hashes['sha1'],
                'sha256_hash': hashes['sha256'],
                'metadata_json': self._extract_additional_metadata(file_path)
            }
        )
        
    def _calculate_file_hashes(self, file_path: Path) -> Dict[str, str]:
        """Calculate MD5, SHA1, and SHA256 hashes for a file"""
        hashes = {
            'md5': '',
            'sha1': '',
            'sha256': ''
        }
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                hashes['md5'] = hashlib.md5(content).hexdigest()
                hashes['sha1'] = hashlib.sha1(content).hexdigest()
                hashes['sha256'] = hashlib.sha256(content).hexdigest()
        except Exception as e:
            print(f"Error calculating hashes for {file_path}: {str(e)}")
            
        return hashes
        
    def _extract_additional_metadata(self, file_path: Path) -> Dict:
        """Extract additional metadata based on file type"""
        metadata = {}
        
        # Add file-specific metadata extraction here
        # This could include:
        # - PDF metadata
        # - Image dimensions
        # - Document properties
        # - etc.
        
        return metadata 