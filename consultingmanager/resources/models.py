"""
Resource Management Models for Consulting Manager.

Includes staff/team management, equipment tracking, offices, and subconsultants.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Office(models.Model):
    """Represents a company office/location (e.g., DLAA offices)"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text="Short code (e.g., 'HNL', 'LA')")
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Office"
        verbose_name_plural = "Offices"

    def __str__(self):
        return f"{self.name} ({self.code})"


class StaffMember(models.Model):
    """Extended profile for staff/team members with billing rates and skills"""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('principal', 'Principal'),
        ('project_manager', 'Project Manager'),
        ('senior_engineer', 'Senior Engineer'),
        ('engineer', 'Engineer'),
        ('junior_engineer', 'Junior Engineer'),
        ('technician', 'Technician'),
        ('intern', 'Intern'),
        ('accounting', 'Accounting'),
        ('administrative', 'Administrative'),
    ]
    
    EMPLOYMENT_STATUS = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contractor', 'Contractor'),
        ('inactive', 'Inactive'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='engineer')
    title = models.CharField(max_length=100, blank=True, help_text="Job title")
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, default='full_time')
    
    # Billing rates
    standard_hourly_rate = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Standard billing rate per hour"
    )
    internal_cost_rate = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Internal cost rate for budget calculations"
    )
    overtime_multiplier = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('1.5'),
        help_text="Multiplier for overtime hours"
    )
    
    # Availability
    weekly_capacity_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('40.0'),
        help_text="Available hours per week"
    )
    
    # Skills and certifications
    skills = models.JSONField(default=list, blank=True, help_text="List of skills/specializations")
    certifications = models.JSONField(default=list, blank=True, help_text="Professional certifications")
    
    # Contact
    phone_extension = models.CharField(max_length=10, blank=True)
    mobile_phone = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=200, blank=True)
    
    # Dates
    hire_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_available(self):
        return self.employment_status != 'inactive' and self.termination_date is None


class ProjectAssignment(models.Model):
    """Tracks staff assignments to projects with role and allocation"""
    ASSIGNMENT_ROLE_CHOICES = [
        ('lead', 'Project Lead'),
        ('manager', 'Project Manager'),
        ('engineer', 'Engineer'),
        ('reviewer', 'Reviewer'),
        ('support', 'Support'),
    ]
    
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='assignments')
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='assignments')
    role = models.CharField(max_length=20, choices=ASSIGNMENT_ROLE_CHOICES, default='engineer')
    allocation_percent = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Percentage of time allocated to this project"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    hourly_rate_override = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Override the staff member's standard rate for this project"
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_active', 'project', 'staff_member']
        unique_together = ['project', 'staff_member']
        verbose_name = "Project Assignment"
        verbose_name_plural = "Project Assignments"

    def __str__(self):
        return f"{self.staff_member.full_name} - {self.project.title} ({self.get_role_display()})"

    @property
    def effective_hourly_rate(self):
        return self.hourly_rate_override or self.staff_member.standard_hourly_rate


class Equipment(models.Model):
    """Acoustic measurement and testing equipment"""
    EQUIPMENT_CATEGORIES = [
        ('sound_level_meter', 'Sound Level Meter'),
        ('analyzer', 'Acoustic Analyzer'),
        ('microphone', 'Microphone'),
        ('calibrator', 'Calibrator'),
        ('vibration', 'Vibration Equipment'),
        ('software', 'Software License'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('calibration', 'Out for Calibration'),
        ('retired', 'Retired'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=EQUIPMENT_CATEGORIES)
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, unique=True)
    asset_tag = models.CharField(max_length=50, blank=True, unique=True, null=True)
    
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipment')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Calibration tracking
    last_calibration_date = models.DateField(null=True, blank=True)
    calibration_due_date = models.DateField(null=True, blank=True)
    calibration_interval_days = models.PositiveIntegerField(default=365, help_text="Days between calibrations")
    calibration_certificate = models.FileField(upload_to='calibration_certs/', null=True, blank=True)
    
    # Financial
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    replacement_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    notes = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True, help_text="Technical specifications")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    @property
    def needs_calibration(self):
        from django.utils import timezone
        if not self.calibration_due_date:
            return False
        return self.calibration_due_date <= timezone.now().date()


class EquipmentUsage(models.Model):
    """Track equipment usage on projects"""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='usage_records')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='equipment_usage')
    checked_out_by = models.ForeignKey(StaffMember, on_delete=models.SET_NULL, null=True, related_name='equipment_checkouts')
    checkout_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)
    purpose = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checkout_date']
        verbose_name = "Equipment Usage"
        verbose_name_plural = "Equipment Usage Records"

    def __str__(self):
        return f"{self.equipment.name} - {self.project.title} ({self.checkout_date.date()})"


class Subconsultant(models.Model):
    """External consultants/contractors used on projects"""
    company_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Specializations
    specialty = models.CharField(max_length=200, blank=True, help_text="Area of expertise")
    services = models.JSONField(default=list, blank=True, help_text="List of services provided")
    
    # Financial
    w9_on_file = models.BooleanField(default=False)
    insurance_on_file = models.BooleanField(default=False)
    insurance_expiration = models.DateField(null=True, blank=True)
    
    # Standard rates
    standard_hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_preferred = models.BooleanField(default=False, help_text="Preferred vendor status")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company_name']
        verbose_name = "Subconsultant"
        verbose_name_plural = "Subconsultants"

    def __str__(self):
        return f"{self.company_name} ({self.contact_name})"


class SubconsultantContract(models.Model):
    """Contracts with subconsultants for specific projects"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    subconsultant = models.ForeignKey(Subconsultant, on_delete=models.CASCADE, related_name='contracts')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='subconsultant_contracts')
    
    contract_number = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    scope_of_work = models.TextField(blank=True)
    
    # Financial
    contract_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_invoiced = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    contract_file = models.FileField(upload_to='subconsultant_contracts/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Subconsultant Contract"
        verbose_name_plural = "Subconsultant Contracts"

    def __str__(self):
        return f"{self.contract_number} - {self.subconsultant.company_name}"

    @property
    def amount_remaining(self):
        return self.contract_amount - self.amount_paid
