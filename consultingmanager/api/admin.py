from django.contrib import admin
from .models import TimelineData

# Register your models here.

@admin.register(TimelineData)
class TimelineDataAdmin(admin.ModelAdmin):
    list_display = ('project', 'last_updated')
    search_fields = ('project__title',)
