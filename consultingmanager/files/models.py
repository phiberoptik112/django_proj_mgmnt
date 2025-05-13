from django.db import models
from django.utils import timezone
from pathlib import Path
import json

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

class ProjectFolder(models.Model):
    """Represents a folder within a project"""
    FOLDER_TYPES = [
        ('BUSINESS', 'Business'),
        ('TECHNICAL', 'Technical'),
        ('ADMIN', 'Administrative'),
        ('OTHER', 'Other'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='folders')
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
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='file_metadata')
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


class RoomAcousticsData(models.Model):
    """Stores room acoustics data"""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='room_acoustics_data')
    folder = models.ForeignKey(ProjectFolder, on_delete=models.CASCADE, related_name='room_acoustics_data')
    room_volume = models.FloatField(null=True, blank=True)
    wall_treatment_materials = models.JSONField(null=True, blank=True)
    wall_treatment_volume = models.FloatField(null=True, blank=True)
    ceiling_treatment_materials = models.JSONField(null=True, blank=True)
    ceiling_treatment_volume = models.FloatField(null=True, blank=True)
    floor_treatment_materials = models.JSONField(null=True, blank=True)
    floor_treatment_volume = models.FloatField(null=True, blank=True)
    class Meta:
        indexes = [
            models.Index(fields=['project', 'folder']),
            ]
    def __str__(self):
        return f"{self.project.project_code} - {self.folder.name} - {self.room_volume}"

class ProjectAnalysis(models.Model):
    """Stores analysis results for projects"""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='analyses')
    analysis_type = models.CharField(max_length=50)  # e.g., 'scope', 'proposal', 'cost'
    analysis_date = models.DateTimeField(default=timezone.now)
    results_json = models.JSONField()  # Stores analysis results in JSON format

    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'analysis_type']),
        ]
        
    def __str__(self):
        return f"{self.project.project_code} - {self.analysis_type}"

class ProjectMetadata(models.Model):
    ANALYSIS_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='metadata')
    project_path = models.CharField(max_length=500, help_text="Full path to the project directory")
    last_analyzed = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ANALYSIS_STATUS, default='pending')
    file_structure_pretty = models.TextField(null=True, blank=True, help_text="Formatted file structure for display")
    email_summary = models.TextField(blank=True, help_text="Summary of processed email content")
    dollar_amounts = models.JSONField(null=True, blank=True, help_text="Extracted dollar amounts from proposals")
    scope_analysis = models.JSONField(null=True, blank=True, help_text="Analysis of scope of work")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Metadata for {self.project.title}"

    def save_file_structure(self, structure_dict):
        """Save file structure as JSON"""
        self.file_structure = json.dumps(structure_dict)
        self.save()

    def save_dollar_amounts(self, amounts_df):
        """Save dollar amounts DataFrame as JSON"""
        self.dollar_amounts = amounts_df.to_json()
        self.save()

    def save_scope_analysis(self, scope_df):
        """Save scope analysis DataFrame as JSON"""
        self.scope_analysis = scope_df.to_json()
        self.save()

    class Meta:
        verbose_name_plural = "Project Metadata"
        ordering = ['-updated_at']

class Email(models.Model):
    """Stores email data"""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='emails')
    folder = models.ForeignKey(ProjectFolder, on_delete=models.CASCADE, related_name='emails')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    sender = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    date = models.DateTimeField()
    attachments = models.JSONField(null=True, blank=True)
    thread_id = models.CharField(max_length=255)
    thread_subject = models.CharField(max_length=255)
    thread_snippet = models.TextField()
    thread_date = models.DateTimeField()
    thread_participants = models.JSONField(null=True, blank=True)
    thread_message_count = models.IntegerField()
    
    def __str__(self):
        return f"{self.project.project_code} - {self.folder.name} - {self.filename}"
    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'folder']),
        ]
    
    def __str__(self):
        return f"{self.project.project_code} - {self.folder.name} - {self.filename}"
    
class Proposal(models.Model):
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='proposals')
    date = models.DateField()
    recipient_name = models.CharField(max_length=255)
    recipient_company = models.CharField(max_length=255)
    recipient_address = models.TextField()
    subject = models.CharField(max_length=255)
    reference = models.CharField(max_length=255, blank=True)
    introduction = models.TextField()
    basic_services = models.JSONField(help_text="List of basic services and descriptions")
    additional_services = models.JSONField(help_text="List of additional services and descriptions", blank=True, null=True)
    compensation = models.JSONField(help_text="Compensation details, fees, terms")
    terms = models.TextField(blank=True)
    attachments = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=[('draft', 'Draft'), ('sent', 'Sent'), ('accepted', 'Accepted')], default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    