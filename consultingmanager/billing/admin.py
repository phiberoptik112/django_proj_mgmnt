from django.contrib import admin
from .models import BillingDetail, ProjectInformationForm, BillingPhase, BillingEmailReference

class BillingPhaseInline(admin.TabularInline):
    model = BillingPhase
    extra = 1
    fields = ['phase_name', 'custom_phase_name', 'max_amount', 'amount', 'subconsultant_fee_1', 'subconsultant_fee_2', 'order']

@admin.register(ProjectInformationForm)
class ProjectInformationFormAdmin(admin.ModelAdmin):
    list_display = ['project', 'project_number', 'client_name', 'billing_contact', 'fee_contract_amount', 'created_at']
    list_filter = ['created_at', 'retainer_received', 'tax_locations']
    search_fields = ['project__title', 'client_name', 'billing_contact', 'project_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Project Identification', {
            'fields': ('project', 'project_number', 'project_name', 'dlaa_office', 
                      'project_location_city', 'project_location_state', 'originator', 'date_entered')
        }),
        ('Client Information', {
            'fields': ('client_name', 'billing_contact', 'billing_contact_email', 
                      'client_project_name', 'purchase_order_number', 'phone')
        }),
        ('Secondary Contact', {
            'fields': ('secondary_contact', 'secondary_contact_email'),
            'classes': ('collapse',)
        }),
        ('Project Management', {
            'fields': ('project_manager', 'project_start_date', 'fee_contract_amount', 
                      'type_of_contract', 'expenses')
        }),
        ('Tax Requirements', {
            'fields': ('tax_locations',),
            'classes': ('collapse',)
        }),
        ('Special Billing', {
            'fields': ('special_negotiated_rates', 'special_invoice_instructions'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('retainer_received', 'additional_comments'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [BillingPhaseInline]

@admin.register(BillingPhase)
class BillingPhaseAdmin(admin.ModelAdmin):
    list_display = ['pif', 'get_phase_display_name', 'amount', 'subconsultant_fee_1', 'subconsultant_fee_2']
    list_filter = ['phase_name']
    search_fields = ['pif__project__title', 'custom_phase_name']
    ordering = ['pif', 'order']

@admin.register(BillingEmailReference)
class BillingEmailReferenceAdmin(admin.ModelAdmin):
    list_display = ['email', 'billing_detail', 'reference_type', 'created_at']
    list_filter = ['reference_type', 'created_at']
    search_fields = ['email__subject', 'billing_detail__invoice_number', 'notes']
    readonly_fields = ['created_at']

@admin.register(BillingDetail)
class BillingDetailAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'project', 'amount', 'status', 'invoice_date', 'due_date']
    list_filter = ['status', 'billing_type', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'project__title', 'project__client__name']
    readonly_fields = ['created_at', 'updated_at']
