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
