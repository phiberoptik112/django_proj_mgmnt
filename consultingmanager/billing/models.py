from django.db import models
from decimal import Decimal

# Create your models here.

class BillingDetail(models.Model):
    BILLING_TYPES = [
        ('hourly', 'Hourly Rate'),
        ('fixed', 'Fixed Price'),
        ('milestone', 'Milestone Based'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='billing_details')
    billing_type = models.CharField(max_length=20, choices=BILLING_TYPES)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.project.title}"

    class Meta:
        ordering = ['-invoice_date']

class ProjectInformationForm(models.Model):
    """PIF - Project Information Form matching the screenshot structure"""
    
    # Project Identification and Originator
    project = models.OneToOneField('projects.Project', on_delete=models.CASCADE, related_name='pif')
    project_number = models.CharField(max_length=50, blank=True, help_text="Unique project identifier")
    project_name = models.CharField(max_length=200, blank=True, help_text="Project name")
    dlaa_office = models.CharField(max_length=100, blank=True, help_text="DLAA Office handling the project")
    project_location_city = models.CharField(max_length=100, blank=True, help_text="Project city")
    project_location_state = models.CharField(max_length=50, blank=True, help_text="Project state")
    originator = models.CharField(max_length=100, blank=True, help_text="Person who initiated the project")
    date_entered = models.DateField(null=True, blank=True, help_text="Date form was completed")
    
    # Client Information
    client_name = models.CharField(max_length=200, blank=True, help_text="Firm or individual name")
    billing_contact = models.CharField(max_length=200, blank=True, help_text="Primary billing contact person")
    billing_contact_email = models.EmailField(blank=True, help_text="Billing contact email address")
    client_project_name = models.CharField(max_length=200, blank=True, help_text="Client's internal project reference")
    purchase_order_number = models.CharField(max_length=100, blank=True, help_text="Purchase order number if applicable")
    phone = models.CharField(max_length=20, blank=True, help_text="Contact phone number")
    
    # Secondary Contact
    secondary_contact = models.CharField(max_length=200, blank=True, help_text="Alternative contact person")
    secondary_contact_email = models.EmailField(blank=True, help_text="Secondary contact email")
    
    # Project Management Details
    project_manager = models.CharField(max_length=200, blank=True, help_text="Assigned project manager")
    project_start_date = models.DateField(null=True, blank=True, help_text="Project commencement date")
    fee_contract_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Total contract fee")
    type_of_contract = models.CharField(max_length=100, blank=True, help_text="Type of contract")
    expenses = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Project expenses")
    
    # Special Tax Requirements
    TAX_LOCATION_CHOICES = [
        ('hawaii', 'Hawaii'),
        ('oahu', 'Oahu'),
        ('maui', 'Maui'),
        ('kauai', 'Kauai'),
        ('japan', 'Japan'),
        ('south_korea', 'South Korea'),
        ('guam', 'Guam'),
        ('singapore', 'Singapore'),
    ]
    tax_locations = models.JSONField(default=list, blank=True, help_text="Selected tax jurisdictions")
    
    # Special Billing Information
    special_negotiated_rates = models.TextField(blank=True, help_text="Special rates if applicable")
    special_invoice_instructions = models.TextField(blank=True, help_text="Specific invoicing instructions")
    
    # Retainer and Comments
    retainer_received_choices = [
        ('yes', 'Yes'),
        ('no', 'No'),
    ]
    retainer_received = models.CharField(max_length=3, choices=retainer_received_choices, blank=True, help_text="Whether retainer has been received")
    additional_comments = models.TextField(blank=True, help_text="Additional notes or comments")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PIF - {self.project.title}"

    class Meta:
        verbose_name = "Project Information Form"
        verbose_name_plural = "Project Information Forms"

class BillingPhase(models.Model):
    """Individual billing phases for the PIF"""
    PHASE_CHOICES = [
        ('professional_services', 'Professional Services'),
        ('programming', 'Programming'),
        ('schematic_design', 'Schematic Design'),
        ('design_development', 'Design Development'),
        ('construction_documents', 'Construction Documents'),
        ('bidding_negotiation', 'Bidding/Negotiation'),
        ('construction_administration', 'Construction Administration'),
        ('general', 'General'),
        ('other', 'Other'),
    ]
    
    pif = models.ForeignKey(ProjectInformationForm, on_delete=models.CASCADE, related_name='billing_phases')
    phase_name = models.CharField(max_length=50, choices=PHASE_CHOICES)
    custom_phase_name = models.CharField(max_length=100, blank=True, help_text="Custom phase name if 'Other' is selected")
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Maximum amount for this phase")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Amount for this phase")
    subconsultant_fee_1 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="First subconsultant fee")
    subconsultant_fee_2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Second subconsultant fee")
    order = models.PositiveIntegerField(default=0, help_text="Order of phases in the form")
    
    class Meta:
        ordering = ['order']
        unique_together = ['pif', 'phase_name', 'order']

    def __str__(self):
        phase_display = self.get_phase_name_display()
        if self.phase_name == 'other' and self.custom_phase_name:
            phase_display = self.custom_phase_name
        return f"{self.pif.project.title} - {phase_display}"

    def get_phase_display_name(self):
        """Get the display name for the phase"""
        if self.phase_name == 'other' and self.custom_phase_name:
            return self.custom_phase_name
        return self.get_phase_name_display()

class BillingEmailReference(models.Model):
    """Links emails to billing records for reference"""
    email = models.ForeignKey('files.Email', on_delete=models.CASCADE, related_name='billing_references')
    billing_detail = models.ForeignKey(BillingDetail, on_delete=models.CASCADE, related_name='email_references')
    reference_type = models.CharField(max_length=20, choices=[
        ('invoice', 'Invoice Email'),
        ('payment', 'Payment Email'),
        ('proposal', 'Proposal Email'),
        ('discussion', 'Billing Discussion'),
        ('reminder', 'Payment Reminder'),
    ])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email.subject} - {self.get_reference_type_display()}"

    class Meta:
        verbose_name = "Billing Email Reference"
        verbose_name_plural = "Billing Email References"

class PIFScanResult(models.Model):
    """Stores results from PIF scanner runs"""
    SCAN_STATUS_CHOICES = [
        ('ingested', 'Ingested'),
        ('skipped', 'Skipped'),
        ('error', 'Error'),
    ]
    
    # Scan identification
    scan_batch = models.ForeignKey('PIFScanBatch', on_delete=models.CASCADE, related_name='scan_results')
    project_number = models.CharField(max_length=50, blank=True, help_text="Extracted project number from path")
    project_name = models.CharField(max_length=200, blank=True, help_text="Extracted project name from path")
    
    # File information
    container_dir = models.TextField(help_text="Full path to the container directory")
    folder_kind = models.CharField(max_length=50, blank=True, help_text="Type of folder (Business, Documents, etc.)")
    pif_file = models.TextField(blank=True, help_text="Full path to the PIF file if found")
    files_count = models.IntegerField(null=True, blank=True, help_text="Number of files in the directory")
    rows = models.IntegerField(null=True, blank=True, help_text="Number of rows in the PIF file")
    
    # Scan results
    status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default='skipped')
    reason = models.TextField(blank=True, help_text="Reason for status (ok, no_pif_found, error message)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to project if found
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True, related_name='pif_scan_results')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "PIF Scan Result"
        verbose_name_plural = "PIF Scan Results"
    
    def __str__(self):
        return f"{self.project_number} - {self.project_name} ({self.status})"
    
    def extract_project_info_from_path(self):
        """Extract project number and name from the container directory path and validate with PIF file"""
        import re
        from pathlib import Path
        
        path = Path(self.container_dir)
        
        # Look for project number pattern in the parent directory name (the actual project folder)
        # This handles paths like /path/to/23-018 Project Name/Business
        parent_dir = path.parent.name
        
        # Look for project number pattern - both PYY-XXX and YY-XXX formats
        # This matches patterns like P23-001, 23-001, P24-123, 24-123, etc.
        project_match = re.search(r'(P?\d{2}-\d{3})', parent_dir)
        
        if project_match:
            extracted_project_number = project_match.group(1)
            
            # Validate the project number by checking if it also appears in the PIF file name
            if self.pif_file:
                pif_path = Path(self.pif_file)
                # Look for both formats in PIF file
                pif_match = re.search(r'(P?\d{2}-\d{3})', pif_path.name)
                
                if pif_match and pif_match.group(1) == extracted_project_number:
                    # Project number matches in both folder and PIF file - use it
                    self.project_number = extracted_project_number
                elif pif_match:
                    # Different project number in PIF file - use the PIF file one (more reliable)
                    self.project_number = pif_match.group(1)
                else:
                    # No project number in PIF file, but found in folder - use folder one
                    self.project_number = extracted_project_number
            else:
                # No PIF file, use the one from folder
                self.project_number = extracted_project_number
            
            # Extract project name (everything after the project number in the parent directory)
            name_parts = parent_dir.split(extracted_project_number, 1)
            if len(name_parts) > 1:
                self.project_name = name_parts[1].strip(' -_')
            else:
                self.project_name = parent_dir
        else:
            # Try to find project number in PIF file if not found in folder
            if self.pif_file:
                pif_path = Path(self.pif_file)
                pif_match = re.search(r'(P?\d{2}-\d{3})', pif_path.name)
                if pif_match:
                    self.project_number = pif_match.group(1)
                    # Try to extract project name from parent directory
                    self.project_name = parent_dir
                else:
                    self.project_name = parent_dir
            else:
                self.project_name = parent_dir
    
    def validate_project_number(self):
        """Validate that the project number is consistent between folder and PIF file"""
        import re
        from pathlib import Path
        
        if not self.project_number or not self.pif_file:
            return False
        
        # Extract project number from PIF file name (both PYY-XXX and YY-XXX formats)
        pif_path = Path(self.pif_file)
        pif_match = re.search(r'(P?\d{2}-\d{3})', pif_path.name)
        
        if pif_match:
            return pif_match.group(1) == self.project_number
        
        return False
    
    def find_matching_project(self):
        """Find the matching project in the database based on project number"""
        if not self.project_number:
            return None
        
        from projects.models import Project
        
        # Try to find by title containing the project number
        try:
            project = Project.objects.filter(title__icontains=self.project_number).first()
            return project
        except:
            pass
        
        return None
    
    def link_to_project(self):
        """Automatically link this scan result to a matching project"""
        project = self.find_matching_project()
        if project:
            self.project = project
            self.save()
            return True
        return False
    
    @classmethod
    def consolidate_duplicates(cls, batch=None):
        """
        Consolidate duplicate scan results for the same project number and name.
        Keeps the result with the most complete information (PIF file, higher file count, etc.)
        """
        from django.db import transaction
        
        if batch:
            queryset = cls.objects.filter(scan_batch=batch)
        else:
            queryset = cls.objects.all()
        
        # Group by project number and name
        project_groups = {}
        for result in queryset:
            if result.project_number and result.project_name:
                key = (result.project_number, result.project_name)
                if key not in project_groups:
                    project_groups[key] = []
                project_groups[key].append(result)
        
        consolidated_count = 0
        deleted_count = 0
        
        with transaction.atomic():
            for (project_number, project_name), results in project_groups.items():
                if len(results) > 1:
                    # Sort by priority: ingested > error > skipped, then by file count, then by rows
                    def sort_priority(result):
                        status_priority = {'ingested': 3, 'error': 2, 'skipped': 1}
                        return (
                            status_priority.get(result.status, 0),
                            result.files_count or 0,
                            result.rows or 0,
                            len(result.pif_file) if result.pif_file else 0
                        )
                    
                    results.sort(key=sort_priority, reverse=True)
                    
                    # Keep the best result
                    primary_result = results[0]
                    
                    # Merge information from other results
                    for result in results[1:]:
                        # Merge container directories (keep both)
                        if result.container_dir and result.container_dir not in primary_result.container_dir:
                            primary_result.container_dir += f"; {result.container_dir}"
                        
                        # Merge folder kinds
                        if result.folder_kind and result.folder_kind not in primary_result.folder_kind:
                            if primary_result.folder_kind:
                                primary_result.folder_kind += f", {result.folder_kind}"
                            else:
                                primary_result.folder_kind = result.folder_kind
                        
                        # Use the best PIF file (longest path, most complete)
                        if result.pif_file and (not primary_result.pif_file or len(result.pif_file) > len(primary_result.pif_file)):
                            primary_result.pif_file = result.pif_file
                        
                        # Use the highest file count
                        if result.files_count and (not primary_result.files_count or result.files_count > primary_result.files_count):
                            primary_result.files_count = result.files_count
                        
                        # Use the highest row count
                        if result.rows and (not primary_result.rows or result.rows > primary_result.rows):
                            primary_result.rows = result.rows
                        
                        # Use the best status (ingested > error > skipped)
                        status_priority = {'ingested': 3, 'error': 2, 'skipped': 1}
                        if status_priority.get(result.status, 0) > status_priority.get(primary_result.status, 0):
                            primary_result.status = result.status
                            primary_result.reason = result.reason
                        
                        # Merge reasons if different
                        if result.reason and result.reason != primary_result.reason:
                            if primary_result.reason and result.reason not in primary_result.reason:
                                primary_result.reason += f"; {result.reason}"
                            elif not primary_result.reason:
                                primary_result.reason = result.reason
                        
                        # Delete the duplicate
                        result.delete()
                        deleted_count += 1
                    
                    # Save the consolidated result
                    primary_result.save()
                    consolidated_count += 1
        
        return consolidated_count, deleted_count

class PIFScanBatch(models.Model):
    """Represents a batch of PIF scans"""
    BATCH_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=200, help_text="Name for this scan batch")
    description = models.TextField(blank=True, help_text="Description of what this scan covers")
    
    # Scan configuration
    year_folders = models.JSONField(default=list, help_text="List of year folder paths to scan")
    scan_date = models.DateTimeField(auto_now_add=True)
    
    # Results
    status = models.CharField(max_length=20, choices=BATCH_STATUS_CHOICES, default='pending')
    total_scanned = models.IntegerField(default=0)
    total_ingested = models.IntegerField(default=0)
    total_skipped = models.IntegerField(default=0)
    total_errors = models.IntegerField(default=0)
    
    # Logging
    log_file = models.TextField(blank=True, help_text="Path to scan log file")
    error_summary = models.TextField(blank=True, help_text="Summary of errors encountered")
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "PIF Scan Batch"
        verbose_name_plural = "PIF Scan Batches"
    
    def __str__(self):
        return f"{self.name} ({self.status}) - {self.scan_date.strftime('%Y-%m-%d %H:%M')}"
    
    def get_summary_stats(self):
        """Get summary statistics for this batch"""
        return {
            'total': self.total_scanned,
            'ingested': self.total_ingested,
            'skipped': self.total_skipped,
            'errors': self.total_errors,
            'success_rate': (self.total_ingested / self.total_scanned * 100) if self.total_scanned > 0 else 0
        }

class PIFScanSchedule(models.Model):
    """Schedule for periodic PIF scanning"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('manual', 'Manual Only'),
    ]
    
    name = models.CharField(max_length=200, help_text="Name for this schedule")
    description = models.TextField(blank=True)
    
    # Schedule configuration
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='manual')
    year_folders = models.JSONField(default=list, help_text="List of year folder paths to scan")
    
    # Schedule details
    is_active = models.BooleanField(default=True, help_text="Whether this schedule is active")
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "PIF Scan Schedule"
        verbose_name_plural = "PIF Scan Schedules"
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"
