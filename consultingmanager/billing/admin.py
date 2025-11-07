from django.contrib import admin
from .models import BillingDetail, ProjectInformationForm, BillingPhase, BillingEmailReference, PIFScanBatch, PIFScanSchedule, PIFScanResult, BillingProgressNote

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

@admin.register(PIFScanResult)
class PIFScanResultAdmin(admin.ModelAdmin):
    list_display = ['project_number', 'project_name', 'status', 'folder_kind', 'project', 'validation_status', 'scan_batch', 'created_at']
    list_filter = ['status', 'folder_kind', 'scan_batch', 'created_at']
    search_fields = ['project_number', 'project_name', 'container_dir', 'pif_file']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def validation_status(self, obj):
        """Show project number validation status"""
        if not obj.project_number or not obj.pif_file:
            return "No PIF file"
        
        if obj.validate_project_number():
            return "✓ Valid"
        else:
            return "✗ Mismatch"
    
    validation_status.short_description = "Validation"
    
    fieldsets = (
        ('Scan Information', {
            'fields': ('scan_batch', 'status', 'reason')
        }),
        ('Project Information', {
            'fields': ('project_number', 'project_name', 'project')
        }),
        ('File Information', {
            'fields': ('container_dir', 'folder_kind', 'pif_file', 'files_count', 'rows')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class PIFScanResultInline(admin.TabularInline):
    model = PIFScanResult
    extra = 0
    readonly_fields = ['project_number', 'project_name', 'status', 'folder_kind', 'created_at']
    fields = ['project_number', 'project_name', 'status', 'folder_kind', 'created_at']
    can_delete = False
    max_num = 50

@admin.register(PIFScanBatch)
class PIFScanBatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'total_scanned', 'total_ingested', 'total_errors', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('name', 'description', 'status')
        }),
        ('Scan Configuration', {
            'fields': ('year_folders',)
        }),
        ('Results', {
            'fields': ('total_scanned', 'total_ingested', 'total_skipped', 'total_errors')
        }),
        ('Logging', {
            'fields': ('log_file', 'error_summary'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PIFScanResultInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('scan_results')

@admin.register(PIFScanSchedule)
class PIFScanScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'frequency', 'is_active', 'last_run', 'next_run', 'created_at']
    list_filter = ['frequency', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'last_run']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Schedule Information', {
            'fields': ('name', 'description', 'frequency', 'is_active')
        }),
        ('Configuration', {
            'fields': ('year_folders',)
        }),
        ('Timing', {
            'fields': ('last_run', 'next_run'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['run_schedule']
    
    def run_schedule(self, request, queryset):
        """Run the selected schedules"""
        from django.core.management import call_command
        
        for schedule in queryset:
            try:
                call_command('run_pif_scans', schedule_id=schedule.id, force=True)
                self.message_user(request, f'Successfully ran schedule: {schedule.name}')
            except Exception as e:
                self.message_user(request, f'Error running schedule {schedule.name}: {str(e)}', level='ERROR')
    
    run_schedule.short_description = "Run selected schedules"

@admin.register(BillingProgressNote)
class BillingProgressNoteAdmin(admin.ModelAdmin):
    list_display = ['project', 'note_text_preview', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['project__title', 'note_text', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def note_text_preview(self, obj):
        """Show a preview of the note text"""
        return obj.note_text[:100] + '...' if len(obj.note_text) > 100 else obj.note_text

    note_text_preview.short_description = "Note Preview"
