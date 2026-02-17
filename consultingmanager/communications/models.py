from django.db import models
from django.template import Template, Context

# Create your models here.

class Communication(models.Model):
    COMMUNICATION_TYPES = [
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('call', 'Phone Call'),
        ('chat', 'Chat'),
        ('other', 'Other'),
    ]

    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='communications')
    communication_type = models.CharField(max_length=20, choices=COMMUNICATION_TYPES)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    date = models.DateTimeField()
    participants = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.communication_type} - {self.subject} - {self.project.title}"

    class Meta:
        ordering = ['-date']


class EmailTemplate(models.Model):
    """Reusable email templates for common communications"""
    TEMPLATE_CATEGORIES = [
        ('proposal', 'Proposal'),
        ('invoice', 'Invoice'),
        ('report', 'Report Delivery'),
        ('meeting', 'Meeting'),
        ('status_update', 'Status Update'),
        ('reminder', 'Reminder'),
        ('thank_you', 'Thank You'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=TEMPLATE_CATEGORIES)
    description = models.TextField(blank=True, help_text="Description of when to use this template")
    
    subject_template = models.CharField(max_length=300, help_text="Email subject (supports Django template syntax)")
    body_template = models.TextField(help_text="Email body (supports Django template syntax)")
    
    # Available template variables documentation
    available_variables = models.JSONField(
        default=list, blank=True,
        help_text="List of available variables: ['project_name', 'client_name', etc.]"
    )
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def render_subject(self, context_dict):
        """Render the subject template with given context"""
        template = Template(self.subject_template)
        return template.render(Context(context_dict))

    def render_body(self, context_dict):
        """Render the body template with given context"""
        template = Template(self.body_template)
        return template.render(Context(context_dict))


class NotificationPreference(models.Model):
    """User preferences for notifications"""
    NOTIFICATION_EVENTS = [
        ('milestone_due', 'Milestone Due'),
        ('milestone_overdue', 'Milestone Overdue'),
        ('invoice_sent', 'Invoice Sent'),
        ('invoice_paid', 'Invoice Paid'),
        ('invoice_overdue', 'Invoice Overdue'),
        ('document_uploaded', 'Document Uploaded'),
        ('document_approved', 'Document Approved'),
        ('assignment_added', 'Project Assignment'),
        ('status_change', 'Project Status Change'),
        ('comment_added', 'Comment Added'),
    ]
    
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notification preferences (JSON field with event: boolean pairs)
    email_notifications = models.JSONField(
        default=dict, blank=True,
        help_text="Email notification settings per event type"
    )
    
    # In-app notification preferences
    app_notifications = models.JSONField(
        default=dict, blank=True,
        help_text="In-app notification settings per event type"
    )
    
    # Digest preferences
    daily_digest = models.BooleanField(default=False, help_text="Receive daily email digest")
    weekly_digest = models.BooleanField(default=True, help_text="Receive weekly email digest")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"

    def __str__(self):
        return f"Notification prefs for {self.user.username}"

    def should_notify_email(self, event_type):
        """Check if user should receive email for this event"""
        return self.email_notifications.get(event_type, True)  # Default to True

    def should_notify_app(self, event_type):
        """Check if user should receive in-app notification for this event"""
        return self.app_notifications.get(event_type, True)


class Notification(models.Model):
    """In-app notifications for users"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error'),
    ]
    
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional links
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True)
    link_url = models.CharField(max_length=500, blank=True, help_text="URL to related object")
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Email tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_as_read(self):
        """Mark this notification as read"""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class EmailLog(models.Model):
    """Log of sent emails for auditing"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True)
    
    subject = models.CharField(max_length=300)
    body = models.TextField()
    
    # Related objects
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    sent_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"

    def __str__(self):
        return f"{self.subject} to {self.recipient_email} ({self.status})"
