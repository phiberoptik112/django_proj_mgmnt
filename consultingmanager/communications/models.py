from django.db import models

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
