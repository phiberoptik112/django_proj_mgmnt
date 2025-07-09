from django.contrib import admin
from .models import Project, ProjectPhase, PhaseWorkLog, Milestone

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
