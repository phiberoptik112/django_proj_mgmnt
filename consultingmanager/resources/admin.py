from django.contrib import admin
from .models import (
    Office, StaffMember, ProjectAssignment, 
    Equipment, EquipmentUsage,
    Subconsultant, SubconsultantContract
)


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'state', 'is_active']
    list_filter = ['is_active', 'state']
    search_fields = ['name', 'code', 'city']


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'role', 'office', 'employment_status', 'standard_hourly_rate']
    list_filter = ['role', 'employment_status', 'office']
    search_fields = ['user__first_name', 'user__last_name', 'user__username', 'employee_id']
    raw_id_fields = ['user']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'employee_id', 'title', 'role', 'employment_status', 'office')
        }),
        ('Billing', {
            'fields': ('standard_hourly_rate', 'internal_cost_rate', 'overtime_multiplier', 'weekly_capacity_hours')
        }),
        ('Skills', {
            'fields': ('skills', 'certifications'),
            'classes': ('collapse',)
        }),
        ('Contact', {
            'fields': ('phone_extension', 'mobile_phone', 'emergency_contact'),
            'classes': ('collapse',)
        }),
        ('Employment Dates', {
            'fields': ('hire_date', 'termination_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ['staff_member', 'project', 'role', 'allocation_percent', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['staff_member__user__first_name', 'staff_member__user__last_name', 'project__title']
    raw_id_fields = ['project', 'staff_member']


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'serial_number', 'status', 'office', 'calibration_due_date']
    list_filter = ['category', 'status', 'office']
    search_fields = ['name', 'serial_number', 'asset_tag', 'manufacturer', 'model_number']
    date_hierarchy = 'last_calibration_date'


@admin.register(EquipmentUsage)
class EquipmentUsageAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'project', 'checked_out_by', 'checkout_date', 'return_date']
    list_filter = ['checkout_date']
    search_fields = ['equipment__name', 'project__title']
    raw_id_fields = ['equipment', 'project', 'checked_out_by']
    date_hierarchy = 'checkout_date'


@admin.register(Subconsultant)
class SubconsultantAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contact_name', 'specialty', 'is_active', 'is_preferred']
    list_filter = ['is_active', 'is_preferred', 'w9_on_file', 'insurance_on_file']
    search_fields = ['company_name', 'contact_name', 'contact_email', 'specialty']


@admin.register(SubconsultantContract)
class SubconsultantContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'subconsultant', 'project', 'contract_amount', 'status']
    list_filter = ['status']
    search_fields = ['contract_number', 'subconsultant__company_name', 'project__title']
    raw_id_fields = ['subconsultant', 'project']
    date_hierarchy = 'start_date'
