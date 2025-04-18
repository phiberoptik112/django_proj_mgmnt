from django.db import models
from django.utils import timezone
from pathlib import Path

# Create your models here.

class File(models.Model):
    FILE_TYPES = [
        ('document', 'Document'),
        ('spreadsheet', 'Spreadsheet'),
        ('presentation', 'Presentation'),
        ('image', 'Image'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='files')
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file = models.FileField(upload_to='project_files/%Y/%m/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.project.title}"

    class Meta:
        ordering = ['-uploaded_at']

class Project(models.Model):
    """Represents a consulting project with its metadata"""
    project_code = models.CharField(max_length=10, unique=True)  # e.g., "23-001"
    name = models.CharField(max_length=255)
    year = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', 'project_code']
        
    def __str__(self):
        return f"{self.project_code} - {self.name}"

class ProjectFolder(models.Model):
    """Represents a folder within a project"""
    FOLDER_TYPES = [
        ('BUSINESS', 'Business'),
        ('TECHNICAL', 'Technical'),
        ('ADMIN', 'Administrative'),
        ('OTHER', 'Other'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='folders')
    name = models.CharField(max_length=255)
    folder_type = models.CharField(max_length=20, choices=FOLDER_TYPES)
    relative_path = models.CharField(max_length=1000)  # Path relative to project root
    parent_folder = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subfolders')
    
    class Meta:
        unique_together = ['project', 'relative_path']
        
    def __str__(self):
        return f"{self.project.project_code} - {self.name}"

class FileMetadata(models.Model):
    """Stores metadata for individual files"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    folder = models.ForeignKey(ProjectFolder, on_delete=models.CASCADE, related_name='files')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    full_path = models.CharField(max_length=1000)
    size_bytes = models.BigIntegerField()
    created_time = models.DateTimeField()
    modified_time = models.DateTimeField()
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    md5_hash = models.CharField(max_length=32, null=True, blank=True)
    sha1_hash = models.CharField(max_length=40, null=True, blank=True)
    sha256_hash = models.CharField(max_length=64, null=True, blank=True)
    extracted_text = models.TextField(null=True, blank=True)
    metadata_json = models.JSONField(default=dict)  # For storing additional metadata
    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'folder']),
            models.Index(fields=['file_type']),
        ]
        
    def __str__(self):
        return f"{self.project.project_code} - {self.filename}"

class ProjectAnalysis(models.Model):
    """Stores analysis results for projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='analyses')
    analysis_type = models.CharField(max_length=50)  # e.g., 'scope', 'proposal', 'cost'
    analysis_date = models.DateTimeField(default=timezone.now)
    results_json = models.JSONField()  # Stores analysis results in JSON format
    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'analysis_type']),
        ]
        
    def __str__(self):
        return f"{self.project.project_code} - {self.analysis_type}"
