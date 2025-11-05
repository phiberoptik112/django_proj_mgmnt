from django.contrib import admin
from .models import Project, ProjectPhase, PhaseWorkLog, Milestone, ScopeItem, RecItem, RecItemVersion, RecItemAttribute, ProposalScanResult, ProjectScopeCategory

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'status', 'start_date', 'end_date', 'budget')
    list_filter = ('status', 'client')
    search_fields = ('title', 'client__name')
    raw_id_fields = ('client',)
    date_hierarchy = 'start_date'

@admin.register(ProjectPhase)
class ProjectPhaseAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'order', 'status', 'percent_complete', 'start_date', 'end_date')
    list_filter = ('status', 'project')
    search_fields = ('name', 'project__title')
    ordering = ('project', 'order')

@admin.register(PhaseWorkLog)
class PhaseWorkLogAdmin(admin.ModelAdmin):
    list_display = ('phase', 'date', 'hours_worked', 'hours_invoiced', 'is_wip')
    list_filter = ('is_wip', 'phase')
    search_fields = ('phase__name', 'phase__project__title')
    ordering = ('phase', 'date')

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'due_date', 'source', 'related_email')
    list_filter = ('source', 'project')
    search_fields = ('name', 'project__title', 'description')
    ordering = ('project', 'due_date')

@admin.register(ScopeItem)
class ScopeItemAdmin(admin.ModelAdmin):
    list_display = ('project', 'category', 'description', 'created_at')
    list_filter = ('category', 'project', 'created_at')
    search_fields = ('category', 'description', 'project__title')
    ordering = ('project', 'category')

@admin.register(RecItem)
class RecItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'scope_item', 'category', 'status', 'priority', 'created_at')
    list_filter = ('category', 'status', 'priority', 'scope_item__project')
    search_fields = ('title', 'description', 'scope_item__category', 'scope_item__project__title')
    ordering = ('scope_item__project', 'category', 'title')
    raw_id_fields = ('scope_item',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('scope_item', 'category', 'title', 'description')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Email Integration', {
            'fields': ('keywords',),
            'description': 'Keywords for automatic email content analysis (comma-separated)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RecItemVersion)
class RecItemVersionAdmin(admin.ModelAdmin):
    list_display = ('rec_item', 'version_number', 'change_source', 'created_at', 'created_by')
    list_filter = ('change_source', 'rec_item__category', 'rec_item__scope_item__project')
    search_fields = ('rec_item__title', 'title', 'description', 'change_notes')
    ordering = ('rec_item', '-version_number')
    raw_id_fields = ('rec_item', 'source_file', 'source_email', 'created_by')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Version Information', {
            'fields': ('rec_item', 'version_number', 'title', 'description')
        }),
        ('Technical Specifications', {
            'fields': ('technical_specs',),
            'description': 'JSON format: {"attribute": "value", "another": "value"}'
        }),
        ('Change Tracking', {
            'fields': ('change_source', 'change_notes')
        }),
        ('Source References', {
            'fields': ('source_file', 'source_email', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(RecItemAttribute)
class RecItemAttributeAdmin(admin.ModelAdmin):
    list_display = ('rec_item', 'name', 'value', 'unit', 'attribute_type')
    list_filter = ('attribute_type', 'rec_item__category', 'rec_item__scope_item__project')
    search_fields = ('name', 'value', 'rec_item__title')
    ordering = ('rec_item', 'name')
    raw_id_fields = ('rec_item',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ProposalScanResult)
class ProposalScanResultAdmin(admin.ModelAdmin):
    list_display = ('project', 'status', 'proposal_file', 'scanned_at')
    list_filter = ('status', 'scanned_at')
    search_fields = ('project__title', 'proposal_file')
    raw_id_fields = ('project',)
    readonly_fields = ('scanned_at', 'updated_at')
    ordering = ('-scanned_at',)

@admin.register(ProjectScopeCategory)
class ProjectScopeCategoryAdmin(admin.ModelAdmin):
    list_display = ('project', 'category_name', 'confidence_score', 'created_at')
    list_filter = ('category_name', 'project', 'created_at')
    search_fields = ('category_name', 'project__title')
    raw_id_fields = ('project', 'scan_result')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('project', '-confidence_score', 'category_name')
