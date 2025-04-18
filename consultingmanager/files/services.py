"""
Service layer for file management operations.
This module provides high-level operations for file management,
integrating with the metadata processor and server file searcher.
"""

import os
from django.conf import settings
from django.core.files.storage import default_storage
from .utils.metadata_processor import FileMetadataProcessor, ServerFileSearcher
from .models import File

class FileService:
    """Service class for file-related operations."""
    
    @staticmethod
    def process_uploaded_file(file_instance: File) -> dict:
        """
        Process an uploaded file and generate its metadata.
        
        Args:
            file_instance: The File model instance
            
        Returns:
            Dictionary containing the processed metadata
        """
        # Get the file path
        file_path = default_storage.path(file_instance.file.name)
        
        # Generate metadata
        processor = FileMetadataProcessor(file_path)
        metadata = processor.generate_metadata()
        
        # Update file instance with metadata
        file_instance.file_type = metadata['content_info']['mime_type']
        file_instance.file_size = metadata['basic_info']['size']
        file_instance.metadata = metadata
        file_instance.save()
        
        return metadata

    @staticmethod
    def search_server_files(query: str, **kwargs) -> list:
        """
        Search for files on the server.
        
        Args:
            query: Search term
            **kwargs: Additional search criteria
            
        Returns:
            List of matching file paths
        """
        # Use the media root as the base path for searching
        base_path = settings.MEDIA_ROOT
        searcher = ServerFileSearcher(base_path)
        
        return searcher.search_files(
            query=query,
            file_types=kwargs.get('file_types'),
            max_size=kwargs.get('max_size'),
            min_size=kwargs.get('min_size')
        )

    @staticmethod
    def sync_server_files():
        """
        Synchronize the database with files on the server.
        This method scans the server's file directory and updates the database accordingly.
        """
        base_path = settings.MEDIA_ROOT
        
        # Get all files in the media directory
        for root, _, files in os.walk(base_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, base_path)
                
                # Check if file exists in database
                if not File.objects.filter(file=relative_path).exists():
                    # Create new file instance
                    file_instance = File(
                        name=os.path.splitext(filename)[0],
                        file=relative_path
                    )
                    file_instance.save()
                    
                    # Process metadata
                    FileService.process_uploaded_file(file_instance)

    @staticmethod
    def get_file_preview(file_instance: File) -> dict:
        """
        Generate a preview for a file.
        
        Args:
            file_instance: The File model instance
            
        Returns:
            Dictionary containing preview information
        """
        preview_info = {
            'can_preview': False,
            'preview_type': None,
            'preview_data': None
        }
        
        file_path = default_storage.path(file_instance.file.name)
        metadata = file_instance.metadata or FileMetadataProcessor(file_path).generate_metadata()
        
        # Determine preview type based on file type
        mime_type = metadata['content_info']['mime_type']
        
        if mime_type:
            if mime_type.startswith('image/'):
                preview_info.update({
                    'can_preview': True,
                    'preview_type': 'image',
                    'preview_data': file_instance.file.url
                })
            elif mime_type.startswith('text/'):
                try:
                    with open(file_path, 'r') as f:
                        preview_info.update({
                            'can_preview': True,
                            'preview_type': 'text',
                            'preview_data': f.read(4096)  # Read first 4KB
                        })
                except Exception:
                    pass
            # Add more preview types as needed
            
        return preview_info 