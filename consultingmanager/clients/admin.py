from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'email', 'phone', 'billing_contact', 'created_at')
    list_filter = ('company',)
    search_fields = ('name', 'company', 'email', 'billing_contact')
    ordering = ('name',)
