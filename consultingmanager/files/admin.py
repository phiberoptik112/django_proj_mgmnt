from django.contrib import admin
from .models import ProjectFolder, FileMetadata, ProjectAnalysis, File, DocumentSummary
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
