from django.db import models

# Create your models here.

class Test(models.Model):
    TEST_TYPES = [
        ('unit', 'Unit Test'),
        ('integration', 'Integration Test'),
        ('system', 'System Test'),
        ('acceptance', 'Acceptance Test'),
    ]

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
    ]

    title = models.CharField(max_length=200)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='tests')
    test_type = models.CharField(max_length=20, choices=TEST_TYPES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.project.title}"

    class Meta:
        ordering = ['-created_at']

class TestData(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='data_files')
    file = models.ForeignKey('files.File', on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Test Data for {self.test.title}"

    class Meta:
        ordering = ['-created_at']
