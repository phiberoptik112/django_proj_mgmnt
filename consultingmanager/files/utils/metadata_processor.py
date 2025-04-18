"""
Metadata processing utilities for file management.
This module handles the creation, extraction, and management of file metadata.
"""

import os
import hashlib
import mimetypes
import magic  # python-magic library for better file type detection
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class FileMetadataProcessor:
    """Handles the processing and creation of file metadata."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        
    def generate_metadata(self) -> Dict[str, Any]:
        """
        Generate comprehensive metadata for a file.
        Returns a dictionary containing all metadata.
        """
        metadata = {
            'basic_info': self._get_basic_info(),
            'content_info': self._get_content_info(),
            'security_info': self._get_security_info(),
            'custom_attributes': self._get_custom_attributes()
        }
        return metadata
    
    def _get_basic_info(self) -> Dict[str, Any]:
        """Get basic file information."""
        stat = self.file_path.stat()
        return {
            'filename': self.file_path.name,
            'size': stat.st_size,
            'created_time': datetime.fromtimestamp(stat.st_ctime),
            'modified_time': datetime.fromtimestamp(stat.st_mtime),
            'accessed_time': datetime.fromtimestamp(stat.st_atime),
            'extension': self.file_path.suffix.lower(),
        }
    
    def _get_content_info(self) -> Dict[str, Any]:
        """Get content-specific information."""
        mime_type, _ = mimetypes.guess_type(str(self.file_path))
        
        try:
            file_type = magic.from_file(str(self.file_path), mime=True)
        except Exception:
            file_type = mime_type
            
        return {
            'mime_type': mime_type,
            'detected_type': file_type,
        }
    
    def _get_security_info(self) -> Dict[str, Any]:
        """Get security-related information."""
        checksums = {}
        
        # Only calculate checksums for files under a certain size (e.g., 100MB)
        if self.file_path.stat().st_size < 100 * 1024 * 1024:
            with open(self.file_path, 'rb') as f:
                content = f.read()
                checksums = {
                    'md5': hashlib.md5(content).hexdigest(),
                    'sha1': hashlib.sha1(content).hexdigest(),
                    'sha256': hashlib.sha256(content).hexdigest(),
                }
        
        return {
            'checksums': checksums,
            'permissions': oct(self.file_path.stat().st_mode)[-3:],
        }
    
    def _get_custom_attributes(self) -> Dict[str, Any]:
        """Get custom/extended attributes specific to your needs."""
        # Add any custom metadata extraction logic here
        return {
            'category': self._determine_category(),
            'tags': self._extract_tags(),
            'searchable_text': self._extract_searchable_text(),
        }
    
    def _determine_category(self) -> str:
        """Determine the category of the file based on type/content."""
        ext = self.file_path.suffix.lower()
        
        # Basic categorization based on extension
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return 'image'
        elif ext in ['.doc', '.docx', '.pdf', '.txt', '.rtf']:
            return 'document'
        elif ext in ['.xls', '.xlsx', '.csv']:
            return 'spreadsheet'
        elif ext in ['.mp4', '.avi', '.mov', '.wmv']:
            return 'video'
        elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
            return 'audio'
        else:
            return 'other'
    
    def _extract_tags(self) -> list:
        """Extract or generate tags based on file attributes."""
        tags = []
        
        # Add basic tags based on category
        category = self._determine_category()
        tags.append(category)
        
        # Add tags based on file size
        size_mb = self.file_path.stat().st_size / (1024 * 1024)
        if size_mb < 1:
            tags.append('small')
        elif size_mb < 10:
            tags.append('medium')
        else:
            tags.append('large')
            
        return tags
    
    def _extract_searchable_text(self) -> Optional[str]:
        """Extract searchable text content if possible."""
        # This is a placeholder - implement based on your needs
        # You might want to use libraries like:
        # - python-docx for Word documents
        # - PyPDF2 for PDFs
        # - pytesseract for images
        # - etc.
        return None

class ServerFileSearcher:
    """Handles searching for files on the server."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
    
    def search_files(self, 
                    query: str, 
                    file_types: Optional[list] = None,
                    max_size: Optional[int] = None,
                    min_size: Optional[int] = None) -> list:
        """
        Search for files matching the given criteria.
        
        Args:
            query: Search term
            file_types: List of file extensions to include
            max_size: Maximum file size in bytes
            min_size: Minimum file size in bytes
            
        Returns:
            List of matching file paths
        """
        results = []
        query = query.lower()
        
        for root, _, files in os.walk(self.base_path):
            for file in files:
                file_path = Path(root) / file
                
                # Skip if file type doesn't match
                if file_types and not any(file.lower().endswith(ft.lower()) for ft in file_types):
                    continue
                    
                # Skip if file size doesn't match criteria
                file_size = file_path.stat().st_size
                if max_size and file_size > max_size:
                    continue
                if min_size and file_size < min_size:
                    continue
                
                # Check if file matches search criteria
                if self._matches_search_criteria(file_path, query):
                    results.append(file_path)
        
        return results
    
    def _matches_search_criteria(self, file_path: Path, query: str) -> bool:
        """Check if a file matches the search criteria."""
        # Match filename
        if query in file_path.name.lower():
            return True
            
        # Match metadata (you can expand this based on your needs)
        try:
            metadata = FileMetadataProcessor(file_path).generate_metadata()
            
            # Check basic info
            if query in str(metadata['basic_info']).lower():
                return True
                
            # Check custom attributes
            if query in str(metadata['custom_attributes']).lower():
                return True
                
        except Exception:
            # Log error if needed
            pass
            
        return False 