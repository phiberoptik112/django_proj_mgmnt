from django.db import models
from django.conf import settings

# Create your models here.

class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='projects')
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.client.name}"

    class Meta:
        ordering = ['-created_at']

class TimeEntry(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField()
    billable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ProjectPhase(models.Model):
    PHASE_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    project = models.ForeignKey('Project', related_name='phases', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    percent_complete = models.FloatField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PHASE_STATUS_CHOICES, default='not_started')

    class Meta:
        ordering = ['project', 'order']
        unique_together = ('project', 'order')

    def __str__(self):
        return f"{self.project.title} - {self.name}"

class PhaseWorkLog(models.Model):
    phase = models.ForeignKey(ProjectPhase, related_name='work_logs', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    hours_worked = models.FloatField(default=0)
    hours_invoiced = models.FloatField(default=0)
    is_wip = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['phase', 'date']

    def __str__(self):
        return f"{self.phase} - {self.date}"

class Milestone(models.Model):
    MILESTONE_SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('email', 'Extracted from Email'),
    ]
    project = models.ForeignKey('Project', related_name='milestones', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    due_date = models.DateField()
    source = models.CharField(max_length=20, choices=MILESTONE_SOURCE_CHOICES, default='manual')
    description = models.TextField(blank=True)
    related_email = models.ForeignKey('files.Email', null=True, blank=True, on_delete=models.SET_NULL, related_name='milestone_links')

    class Meta:
        ordering = ['project', 'due_date']

    def __str__(self):
        return f"{self.project.title} - {self.name} ({self.due_date})"

class ScopeItem(models.Model):
    project = models.ForeignKey('Project', related_name='scope_items', on_delete=models.CASCADE)
    milestone = models.ForeignKey('Milestone', related_name='scope_items', on_delete=models.SET_NULL, null=True, blank=True)
    phase = models.ForeignKey('ProjectPhase', related_name='scope_items', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=100)
    description = models.TextField()
    source_file = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}: {self.description[:30]}"