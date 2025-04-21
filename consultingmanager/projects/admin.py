from django.contrib import admin
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'status', 'start_date', 'end_date', 'budget')
    list_filter = ('status', 'client')
    search_fields = ('title', 'client__name')
    raw_id_fields = ('client',)
    date_hierarchy = 'start_date'
