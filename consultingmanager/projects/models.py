from django.db import models
from django.conf import settings

# Create your models here.

class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='projects')
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.client.name}"

    class Meta:
        ordering = ['-created_at']

class TimeEntry(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField()
    billable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ProjectPhase(models.Model):
    PHASE_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    project = models.ForeignKey('Project', related_name='phases', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    percent_complete = models.FloatField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PHASE_STATUS_CHOICES, default='not_started')

    class Meta:
        ordering = ['project', 'order']
        unique_together = ('project', 'order')

    def __str__(self):
        return f"{self.project.title} - {self.name}"

class PhaseWorkLog(models.Model):
    phase = models.ForeignKey(ProjectPhase, related_name='work_logs', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    hours_worked = models.FloatField(default=0)
    hours_invoiced = models.FloatField(default=0)
    is_wip = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['phase', 'date']

    def __str__(self):
        return f"{self.phase} - {self.date}"

class Milestone(models.Model):
    MILESTONE_SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('email', 'Extracted from Email'),
    ]
    project = models.ForeignKey('Project', related_name='milestones', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    due_date = models.DateField()
    source = models.CharField(max_length=20, choices=MILESTONE_SOURCE_CHOICES, default='manual')
    description = models.TextField(blank=True)
    related_email = models.ForeignKey('files.Email', null=True, blank=True, on_delete=models.SET_NULL, related_name='milestone_links')

    class Meta:
        ordering = ['project', 'due_date']

    def __str__(self):
        return f"{self.project.title} - {self.name} ({self.due_date})"

class ScopeItem(models.Model):
    project = models.ForeignKey('Project', related_name='scope_items', on_delete=models.CASCADE)
    milestone = models.ForeignKey('Milestone', related_name='scope_items', on_delete=models.SET_NULL, null=True, blank=True)
    phase = models.ForeignKey('ProjectPhase', related_name='scope_items', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=100)
    description = models.TextField()
    source_file = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}: {self.description[:30]}"

class RecItem(models.Model):
    """Recommendation items - sub-categories of scope items for tracking acoustic recommendations over time"""
    ACOUSTIC_CATEGORIES = [
        ('sound_isolation', 'Sound Isolation'),
        ('mechanical_noise_vibration', 'Mechanical Noise & Vibration'),
        ('room_acoustics', 'Room Acoustics'),
        ('environmental_noise', 'Environmental Noise'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Client'),
        ('under_review', 'Under Client Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('implemented', 'Implemented'),
        ('modified', 'Modified'),
    ]
    
    scope_item = models.ForeignKey('ScopeItem', on_delete=models.CASCADE, related_name='rec_items')
    category = models.CharField(max_length=50, choices=ACOUSTIC_CATEGORIES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=20, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    keywords = models.TextField(blank=True, help_text="Keywords for email content analysis (comma-separated)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.scope_item.category}: {self.title}"

    class Meta:
        ordering = ['scope_item', 'category', 'title']

    def get_latest_version(self):
        """Get the most recent version of this RecItem"""
        return self.versions.order_by('-version_number').first()

    def create_new_version(self, title, description, technical_specs, source_file=None, source_email=None, created_by=None):
        """Create a new version of this RecItem"""
        latest_version = self.get_latest_version()
        new_version_number = (latest_version.version_number + 1) if latest_version else 1
        
        version = RecItemVersion.objects.create(
            rec_item=self,
            version_number=new_version_number,
            title=title,
            description=description,
            technical_specs=technical_specs,
            source_file=source_file,
            source_email=source_email,
            created_by=created_by
        )
        
        # Update the main RecItem with latest info
        self.title = title
        self.description = description
        self.save()
        
        return version

class RecItemVersion(models.Model):
    """Tracks individual versions of RecItems with change history"""
    CHANGE_SOURCES = [
        ('manual', 'Manual Entry'),
        ('drawing', 'Drawing Update'),
        ('email', 'Email Communication'),
        ('meeting', 'Meeting Notes'),
        ('report', 'Report Update'),
        ('client_feedback', 'Client Feedback'),
    ]
    
    rec_item = models.ForeignKey('RecItem', on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    technical_specs = models.JSONField(default=dict, help_text="Technical specifications as key-value pairs")
    change_source = models.CharField(max_length=20, choices=CHANGE_SOURCES, default='manual')
    source_file = models.ForeignKey('files.File', on_delete=models.SET_NULL, null=True, blank=True, related_name='rec_item_versions')
    source_email = models.ForeignKey('files.Email', on_delete=models.SET_NULL, null=True, blank=True, related_name='rec_item_versions')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    change_notes = models.TextField(blank=True, help_text="Notes about what changed in this version")

    class Meta:
        unique_together = ['rec_item', 'version_number']
        ordering = ['rec_item', 'version_number']

    def __str__(self):
        return f"{self.rec_item.title} - v{self.version_number}"

    def get_previous_version(self):
        """Get the previous version of this RecItem"""
        return RecItemVersion.objects.filter(
            rec_item=self.rec_item,
            version_number__lt=self.version_number
        ).order_by('-version_number').first()

    def get_changes_from_previous(self):
        """Compare this version with the previous version and return changes"""
        previous = self.get_previous_version()
        if not previous:
            return {
                'title': 'Initial version',
                'description': 'Initial version',
                'technical_specs': 'Initial version'
            }
        
        changes = {}
        
        if self.title != previous.title:
            changes['title'] = f"Changed from '{previous.title}' to '{self.title}'"
        
        if self.description != previous.description:
            changes['description'] = 'Description updated'
        
        # Compare technical specs
        if self.technical_specs != previous.technical_specs:
            changes['technical_specs'] = 'Technical specifications updated'
        
        return changes

class RecItemAttribute(models.Model):
    """Flexible attributes for RecItems - allows custom technical specifications"""
    ATTRIBUTE_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('file', 'File Reference'),
        ('measurement', 'Measurement with Units'),
    ]
    
    rec_item = models.ForeignKey('RecItem', on_delete=models.CASCADE, related_name='attributes')
    name = models.CharField(max_length=100, help_text="Attribute name, e.g., 'Insertion Loss', 'Silencer Size'")
    value = models.TextField()
    unit = models.CharField(max_length=20, blank=True, help_text="Unit of measurement, e.g., 'dB', 'inches'")
    attribute_type = models.CharField(max_length=20, choices=ATTRIBUTE_TYPES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['rec_item', 'name']
        ordering = ['rec_item', 'name']

    def __str__(self):
        unit_str = f" {self.unit}" if self.unit else ""
        return f"{self.name}: {self.value}{unit_str}"

    def get_display_value(self):
        """Get the formatted display value with units"""
        if self.unit:
            return f"{self.value} {self.unit}"
        return self.value

class ProposalScanResult(models.Model):
    """Stores results from proposal scanner runs"""
    SCAN_STATUS_CHOICES = [
        ('found', 'Proposal Found'),
        ('not_found', 'No Proposal Found'),
        ('error', 'Error'),
    ]
    
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='proposal_scan_results')
    proposal_file = models.CharField(max_length=1000, blank=True, help_text="Full path to the proposal file if found")
    raw_text = models.TextField(blank=True, help_text="Extracted text from the proposal document")
    status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default='not_found')
    error_message = models.TextField(blank=True, help_text="Error message if scan failed")
    scanned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scanned_at']
        verbose_name = "Proposal Scan Result"
        verbose_name_plural = "Proposal Scan Results"
    
    def __str__(self):
        return f"Proposal Scan - {self.project.title} ({self.status})"

class ProjectScopeCategory(models.Model):
    """Stores scope categories for projects extracted from proposals"""
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='scope_categories')
    category_name = models.CharField(max_length=200, help_text="Scope category name (e.g., 'Emergency Generator Noise', 'STC Testing')")
    confidence_score = models.FloatField(default=0.0, help_text="Confidence score from keyword matching (0.0 to 1.0)")
    source_file = models.CharField(max_length=1000, blank=True, help_text="Source proposal file path")
    scan_result = models.ForeignKey('ProposalScanResult', on_delete=models.SET_NULL, null=True, blank=True, related_name='detected_categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['project', '-confidence_score', 'category_name']
        unique_together = ['project', 'category_name']
        verbose_name = "Project Scope Category"
        verbose_name_plural = "Project Scope Categories"
    
    def __str__(self):
        return f"{self.project.title} - {self.category_name}"