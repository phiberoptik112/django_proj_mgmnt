# Role-Based Permissions Implementation Guide

This document outlines the plan for implementing role-based permissions in the Consulting Manager application when ready for multi-user access.

## Overview

The system will support four primary roles with different access levels:
- **Admin**: Full system access
- **Project Manager (PM)**: Project and client management, billing view
- **Engineer**: Project work, time entry, file access
- **Accounting**: Billing, invoices, expenses, financial reports

## Implementation Steps

### 1. Create Permission Groups

Using Django's built-in Groups and Permissions:

```python
# management/commands/setup_permissions.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Create groups
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        pm_group, _ = Group.objects.get_or_create(name='Project Manager')
        engineer_group, _ = Group.objects.get_or_create(name='Engineer')
        accounting_group, _ = Group.objects.get_or_create(name='Accounting')
        
        # Assign permissions to groups
        # Admin gets all permissions
        admin_group.permissions.set(Permission.objects.all())
        
        # PM permissions
        pm_permissions = [
            'add_project', 'change_project', 'view_project',
            'add_client', 'change_client', 'view_client',
            'add_milestone', 'change_milestone', 'view_milestone',
            'view_billingdetail', 'view_expense',
            # ... add more as needed
        ]
        
        # Engineer permissions
        engineer_permissions = [
            'view_project', 'change_project',
            'add_timeentry', 'change_timeentry', 'view_timeentry',
            'add_file', 'change_file', 'view_file',
            'view_documentrevision', 'add_documentrevision',
            # ... add more as needed
        ]
        
        # Accounting permissions
        accounting_permissions = [
            'view_project', 'view_client',
            'add_billingdetail', 'change_billingdetail', 'view_billingdetail',
            'add_expense', 'change_expense', 'view_expense',
            'add_invoice', 'change_invoice', 'view_invoice',
            'view_contract', 'add_contract', 'change_contract',
            # ... add more as needed
        ]
```

### 2. Create Custom Permission Mixin

```python
# core/mixins.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin(UserPassesTestMixin):
    required_roles = []  # Override in view
    
    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=self.required_roles).exists()

class ProjectAccessMixin(UserPassesTestMixin):
    """Check if user has access to specific project"""
    
    def test_func(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='Admin').exists():
            return True
        
        # Check if user is assigned to this project
        project_id = self.kwargs.get('pk') or self.kwargs.get('project_id')
        if project_id:
            from resources.models import ProjectAssignment
            return ProjectAssignment.objects.filter(
                project_id=project_id,
                staff_member__user=user,
                is_active=True
            ).exists()
        return False
```

### 3. Update Views with Permission Checks

```python
# Example view update
from core.mixins import RoleRequiredMixin, ProjectAccessMixin

class ProjectCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    required_roles = ['Admin', 'Project Manager']
    model = Project
    # ...

class BillingDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    required_roles = ['Admin', 'Project Manager', 'Accounting']
    model = BillingDetail
    # ...

class TimeEntryCreateView(LoginRequiredMixin, ProjectAccessMixin, CreateView):
    # Engineers can only add time to projects they're assigned to
    model = TimeEntry
    # ...
```

### 4. Template Permission Checks

```html
{% if perms.projects.add_project %}
    <a href="{% url 'projects:project-create' %}" class="btn btn-primary">New Project</a>
{% endif %}

{% if request.user.groups.all|length > 0 %}
    {% for group in request.user.groups.all %}
        {% if group.name == 'Accounting' %}
            <!-- Show accounting-specific menu items -->
        {% endif %}
    {% endfor %}
{% endif %}
```

### 5. Permission Matrix

| Feature | Admin | PM | Engineer | Accounting |
|---------|-------|-----|----------|------------|
| **Projects** |
| Create Project | Yes | Yes | No | No |
| Edit Project | Yes | Yes | No | No |
| View Project | Yes | Yes | Assigned | No |
| Delete Project | Yes | No | No | No |
| **Clients** |
| Create/Edit Client | Yes | Yes | No | No |
| View Client | Yes | Yes | No | Yes |
| **Time Entries** |
| Add Time Entry | Yes | Yes | Yes | No |
| Edit Own Time | Yes | Yes | Yes | No |
| Edit All Time | Yes | Yes | No | No |
| **Billing** |
| Create Invoice | Yes | No | No | Yes |
| Edit Invoice | Yes | No | No | Yes |
| View Invoice | Yes | Yes | No | Yes |
| **Expenses** |
| Submit Expense | Yes | Yes | Yes | Yes |
| Approve Expense | Yes | Yes | No | Yes |
| **Files** |
| Upload Files | Yes | Yes | Yes | No |
| Delete Files | Yes | Yes | No | No |
| **Resources** |
| Manage Staff | Yes | No | No | No |
| View Staff | Yes | Yes | Yes | Yes |
| Equipment Checkout | Yes | Yes | Yes | No |
| **Reports** |
| Financial Reports | Yes | Yes | No | Yes |
| Project Reports | Yes | Yes | Yes | No |

### 6. Database Changes

Link StaffMember to Django User and Groups:

```python
# In resources/models.py - already implemented
class StaffMember(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    # ...
```

### 7. Middleware for Global Permission Checks (Optional)

```python
# core/middleware.py
class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Add role info to request for easy access
            request.user_roles = list(request.user.groups.values_list('name', flat=True))
            request.is_admin = 'Admin' in request.user_roles
            request.is_pm = 'Project Manager' in request.user_roles
            request.is_engineer = 'Engineer' in request.user_roles
            request.is_accounting = 'Accounting' in request.user_roles
        return self.get_response(request)
```

## Migration Path

1. Run `python manage.py setup_permissions` to create groups
2. Assign existing users to appropriate groups via admin
3. Add `RoleRequiredMixin` to views incrementally
4. Test each role's access thoroughly
5. Update templates to show/hide elements based on permissions

## Testing Checklist

- [ ] Admin can access all features
- [ ] PM can create/edit projects and clients
- [ ] Engineer can only see assigned projects
- [ ] Engineer can add time entries to assigned projects only
- [ ] Accounting can access all billing features
- [ ] Accounting cannot modify project details
- [ ] Unauthorized access returns 403 Forbidden
- [ ] Navigation shows only permitted items per role

## Notes

- Current state: Single developer, no role restrictions needed
- All views currently use `LoginRequiredMixin` only
- When ready for multi-user, implement above incrementally
- Consider django-guardian for object-level permissions if needed
