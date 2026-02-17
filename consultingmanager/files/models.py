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

class DocumentSummary(models.Model):
    """Stores Markdown and summaries generated from PDFs for easier billing context."""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='document_summaries')
    file = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, blank=True, related_name='document_summaries')
    source_path = models.CharField(max_length=1000, blank=True, help_text="Filesystem path if not from uploaded File")
    title = models.CharField(max_length=255, help_text="Title inferred from the document", blank=True)
    page_count = models.PositiveIntegerField(default=0)
    markdown = models.TextField(help_text="Markdown representation of the PDF content")
    summary = models.TextField(help_text="Concise summary for billing context")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='processed', choices=[
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ])

    class Meta:
        indexes = [
            models.Index(fields=['project', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self) -> str:
        base = self.title or (self.file.title if self.file else self.source_path)
        return f"Summary for {base or 'document'}"

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
    
    class Meta:
        indexes = [
            models.Index(fields=['project', 'folder']),
        ]
    
    def __str__(self):
        return f"{self.project.title} - {self.folder.name} - {self.filename}"
    
class Proposal(models.Model):
    # read in proposal data from pdf - use proposal_parser.py to extract data from pdf
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='proposals')
    date = models.DateField()
    recipient_name = models.CharField(max_length=255)
    recipient_company = models.CharField(max_length=255)
    recipient_address = models.TextField()
    # subject = models.CharField(max_length=255)
    # reference = models.CharField(max_length=255, blank=True)
    # introduction = models.TextField()
    basic_services = models.JSONField(help_text="List of basic services and descriptions")
    additional_services = models.JSONField(help_text="List of additional services and descriptions", blank=True, null=True)
    compensation = models.JSONField(help_text="Compensation details, fees, terms")
    # terms = models.TextField(blank=True)
    # attachments = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=[('draft', 'Draft'), ('sent', 'Sent'), ('accepted', 'Accepted')], default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DocumentRevision(models.Model):
    """Track document revisions with version control"""
    DOCUMENT_TYPES = [
        ('report', 'Report'),
        ('proposal', 'Proposal'),
        ('memo', 'Memo'),
        ('letter', 'Letter'),
        ('specification', 'Specification'),
        ('drawing', 'Drawing'),
        ('calculation', 'Calculation'),
        ('other', 'Other'),
    ]
    
    REVISION_STATUS = [
        ('draft', 'Draft'),
        ('internal_review', 'Internal Review'),
        ('client_review', 'Client Review'),
        ('approved', 'Approved'),
        ('superseded', 'Superseded'),
        ('final', 'Final'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='document_revisions')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=300)
    document_number = models.CharField(max_length=50, blank=True, help_text="Internal document number")
    
    # Version tracking
    revision_number = models.CharField(max_length=20, help_text="e.g., A, B, 1, 2, or 1.0, 1.1")
    revision_date = models.DateField()
    status = models.CharField(max_length=20, choices=REVISION_STATUS, default='draft')
    
    # File
    file = models.FileField(upload_to='document_revisions/%Y/%m/')
    file_format = models.CharField(max_length=20, blank=True, help_text="PDF, DOCX, etc.")
    
    # Review/Approval workflow
    prepared_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='prepared_documents')
    reviewed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_documents')
    review_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_documents')
    approval_date = models.DateField(null=True, blank=True)
    
    # Client feedback
    client_approved = models.BooleanField(default=False)
    client_approval_date = models.DateField(null=True, blank=True)
    client_comments = models.TextField(blank=True)
    
    # Tracking
    description = models.TextField(blank=True, help_text="Description of changes in this revision")
    is_current = models.BooleanField(default=True, help_text="Is this the current/latest revision")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'document_number', '-revision_date']
        unique_together = ['project', 'document_number', 'revision_number']
        verbose_name = "Document Revision"
        verbose_name_plural = "Document Revisions"

    def __str__(self):
        return f"{self.title} - Rev {self.revision_number}"

    def save(self, *args, **kwargs):
        # Auto-detect file format from extension
        if self.file and not self.file_format:
            import os
            ext = os.path.splitext(self.file.name)[1].upper().replace('.', '')
            self.file_format = ext
        super().save(*args, **kwargs)

    def mark_as_superseded(self):
        """Mark this revision as superseded when a new one is created"""
        self.status = 'superseded'
        self.is_current = False
        self.save()


class DocumentComment(models.Model):
    """Comments/feedback on document revisions"""
    COMMENT_TYPES = [
        ('internal', 'Internal Comment'),
        ('client', 'Client Comment'),
        ('resolution', 'Resolution'),
    ]
    
    document = models.ForeignKey(DocumentRevision, on_delete=models.CASCADE, related_name='comments')
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES, default='internal')
    
    page_reference = models.CharField(max_length=50, blank=True, help_text="Page or section reference")
    comment_text = models.TextField()
    
    is_resolved = models.BooleanField(default=False)
    resolution_text = models.TextField(blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_comments')
    
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='document_comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['document', 'created_at']
        verbose_name = "Document Comment"
        verbose_name_plural = "Document Comments"

    def __str__(self):
        return f"{self.document.title} - {self.get_comment_type_display()}"


class EmailScanBatch(models.Model):
    """Batch of email scans for extracting timeline events"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey('projects.Project', null=True, blank=True, on_delete=models.CASCADE, 
                                related_name='email_scan_batches',
                                help_text="Scan emails for a specific project")
    folder_paths = models.JSONField(default=list, blank=True, 
                                    help_text="List of folder paths to scan for .msg files")
    
    # Scan options
    scan_date_from = models.DateField(null=True, blank=True, help_text="Only scan emails after this date")
    scan_date_to = models.DateField(null=True, blank=True, help_text="Only scan emails before this date")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_emails_scanned = models.IntegerField(default=0)
    total_events_found = models.IntegerField(default=0)
    total_milestones_created = models.IntegerField(default=0)
    
    error_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Email Scan Batch"
        verbose_name_plural = "Email Scan Batches"

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def get_summary_stats(self):
        return {
            'total_emails': self.total_emails_scanned,
            'total_events': self.total_events_found,
            'pending_review': self.events.filter(status='pending').count(),
            'confirmed': self.events.filter(status='confirmed').count(),
            'converted': self.events.filter(status='converted').count(),
            'rejected': self.events.filter(status='rejected').count(),
        }


class EmailTimelineEvent(models.Model):
    """Extracted timeline waypoint from email content"""
    EVENT_TYPES = [
        ('deadline', 'Deadline'),
        ('meeting', 'Meeting'),
        ('submittal', 'Submittal/Delivery'),
        ('milestone', 'Milestone'),
        ('kickoff', 'Project Kickoff'),
        ('site_visit', 'Site Visit'),
        ('review', 'Review Period'),
        ('approval', 'Approval'),
        ('completion', 'Completion'),
        ('invoice', 'Invoice/Payment'),
        ('change_order', 'Change Order'),
        ('other', 'Other'),
    ]
    
    CONFIDENCE_LEVELS = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted to Milestone'),
    ]
    
    scan_batch = models.ForeignKey(EmailScanBatch, on_delete=models.CASCADE, related_name='events')
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='timeline_events')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='email_timeline_events')
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    event_date = models.DateField()
    event_description = models.CharField(max_length=500)
    
    # Extraction metadata
    extracted_text = models.TextField(help_text="The text snippet that triggered extraction")
    confidence = models.CharField(max_length=10, choices=CONFIDENCE_LEVELS, default='medium')
    extraction_method = models.CharField(max_length=50, help_text="e.g., 'regex', 'keyword', 'pattern'")
    
    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='reviewed_email_events')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # If converted to milestone
    milestone = models.ForeignKey('projects.Milestone', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='source_email_events')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event_date', '-confidence']
        verbose_name = "Email Timeline Event"
        verbose_name_plural = "Email Timeline Events"
        indexes = [
            models.Index(fields=['project', 'event_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()}: {self.event_description[:50]} ({self.event_date})"

    def convert_to_milestone(self, user=None):
        """Convert this event to a project milestone"""
        from projects.models import Milestone
        
        if self.milestone:
            return self.milestone
        
        milestone = Milestone.objects.create(
            project=self.project,
            name=self.event_description[:200],
            due_date=self.event_date,
            source='email',
            description=f"Extracted from email on {self.email.date.strftime('%Y-%m-%d') if self.email.date else 'unknown date'}.\n\nContext: {self.extracted_text[:500]}",
            related_email=self.email
        )
        
        self.milestone = milestone
        self.status = 'converted'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
        
        return milestone


class ProjectStatusIndicator(models.Model):
    """Inferred project status/phase from email patterns"""
    INDICATOR_TYPES = [
        ('phase_start', 'Phase Start'),
        ('phase_complete', 'Phase Complete'),
        ('deliverable_sent', 'Deliverable Sent'),
        ('client_approval', 'Client Approval'),
        ('waiting_on_client', 'Waiting on Client'),
        ('active_work', 'Active Work'),
        ('on_hold', 'On Hold'),
        ('issue_flagged', 'Issue Flagged'),
    ]
    
    scan_batch = models.ForeignKey(EmailScanBatch, on_delete=models.CASCADE, related_name='indicators')
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='status_indicators')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='email_status_indicators')
    
    indicator_type = models.CharField(max_length=30, choices=INDICATOR_TYPES)
    indicator_date = models.DateField()
    description = models.TextField()
    extracted_text = models.TextField()
    confidence = models.CharField(max_length=10, choices=EmailTimelineEvent.CONFIDENCE_LEVELS, default='medium')
    
    # Phase inference
    inferred_phase = models.CharField(max_length=100, blank=True, help_text="Inferred project phase name")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-indicator_date']
        verbose_name = "Project Status Indicator"
        verbose_name_plural = "Project Status Indicators"

    def __str__(self):
        return f"{self.project.title} - {self.get_indicator_type_display()} ({self.indicator_date})"