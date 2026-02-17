from django.contrib import admin
from .models import (
    ProjectFolder, FileMetadata, ProjectAnalysis, File, DocumentSummary,
    EmailScanBatch, EmailTimelineEvent, ProjectStatusIndicator
)
from projects.models import Project

@admin.register(ProjectFolder)
class ProjectFolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'folder_type', 'relative_path')
    list_filter = ('folder_type', 'project')
    search_fields = ('name', 'project__project_code')
    raw_id_fields = ('project', 'parent_folder')

@admin.register(FileMetadata)
class FileMetadataAdmin(admin.ModelAdmin):
    list_display = ('filename', 'project', 'folder', 'file_type', 'size_bytes', 'modified_time')
    list_filter = ('file_type', 'project', 'folder')
    search_fields = ('filename', 'project__project_code', 'folder__name')
    raw_id_fields = ('project', 'folder')
    readonly_fields = ('md5_hash', 'sha1_hash', 'sha256_hash', 'metadata_json')

@admin.register(ProjectAnalysis)
class ProjectAnalysisAdmin(admin.ModelAdmin):
    list_display = ('project', 'analysis_type', 'analysis_date')
    list_filter = ('analysis_type', 'project')
    search_fields = ('project__project_code',)
    raw_id_fields = ('project',)
    readonly_fields = ('results_json',)

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'file_type', 'uploaded_at')
    list_filter = ('file_type', 'project')
    search_fields = ('title', 'project__title')
    raw_id_fields = ('project',)

@admin.register(DocumentSummary)
class DocumentSummaryAdmin(admin.ModelAdmin):
    list_display = ('project', 'title', 'file', 'page_count', 'status', 'created_at')
    list_filter = ('status', 'project')
    search_fields = ('title', 'project__title', 'source_path')
    raw_id_fields = ('project', 'file')
    readonly_fields = ('created_at', 'updated_at')


class EmailTimelineEventInline(admin.TabularInline):
    model = EmailTimelineEvent
    extra = 0
    readonly_fields = ('event_type', 'event_date', 'event_description', 'confidence', 'status')
    fields = ('event_type', 'event_date', 'event_description', 'confidence', 'status')
    can_delete = False
    max_num = 20


@admin.register(EmailScanBatch)
class EmailScanBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'total_emails_scanned', 'total_events_found', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description', 'project__title')
    raw_id_fields = ('project',)
    readonly_fields = ('started_at', 'completed_at', 'total_emails_scanned', 'total_events_found', 
                       'total_milestones_created', 'created_at', 'updated_at')
    inlines = [EmailTimelineEventInline]
    
    fieldsets = (
        ('Batch Info', {
            'fields': ('name', 'description', 'project', 'status')
        }),
        ('Scan Options', {
            'fields': ('folder_paths', 'scan_date_from', 'scan_date_to'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_emails_scanned', 'total_events_found', 'total_milestones_created'),
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Errors', {
            'fields': ('error_summary',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailTimelineEvent)
class EmailTimelineEventAdmin(admin.ModelAdmin):
    list_display = ('event_description_short', 'project', 'event_type', 'event_date', 'confidence', 'status')
    list_filter = ('event_type', 'confidence', 'status', 'created_at')
    search_fields = ('event_description', 'project__title', 'extracted_text')
    raw_id_fields = ('scan_batch', 'email', 'project', 'reviewed_by', 'milestone')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'event_date'
    
    fieldsets = (
        ('Event Info', {
            'fields': ('project', 'event_type', 'event_date', 'event_description')
        }),
        ('Source', {
            'fields': ('scan_batch', 'email', 'extraction_method', 'confidence'),
        }),
        ('Extracted Text', {
            'fields': ('extracted_text',),
            'classes': ('collapse',)
        }),
        ('Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes'),
        }),
        ('Milestone', {
            'fields': ('milestone',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_confirmed', 'mark_rejected', 'convert_to_milestones']
    
    def event_description_short(self, obj):
        return obj.event_description[:50] + '...' if len(obj.event_description) > 50 else obj.event_description
    event_description_short.short_description = 'Description'
    
    def mark_confirmed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='confirmed', 
            reviewed_by=request.user, 
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} events marked as confirmed.')
    mark_confirmed.short_description = 'Mark selected as confirmed'
    
    def mark_rejected(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} events marked as rejected.')
    mark_rejected.short_description = 'Mark selected as rejected'
    
    def convert_to_milestones(self, request, queryset):
        converted = 0
        for event in queryset.filter(status__in=['pending', 'confirmed']):
            try:
                event.convert_to_milestone(user=request.user)
                converted += 1
            except Exception as e:
                self.message_user(request, f'Error converting event {event.id}: {str(e)}', level='ERROR')
        self.message_user(request, f'{converted} events converted to milestones.')
    convert_to_milestones.short_description = 'Convert selected to milestones'


@admin.register(ProjectStatusIndicator)
class ProjectStatusIndicatorAdmin(admin.ModelAdmin):
    list_display = ('project', 'indicator_type', 'indicator_date', 'inferred_phase', 'confidence')
    list_filter = ('indicator_type', 'confidence', 'inferred_phase')
    search_fields = ('project__title', 'description', 'extracted_text')
    raw_id_fields = ('scan_batch', 'email', 'project')
    readonly_fields = ('created_at',)
    date_hierarchy = 'indicator_date'
