from django.db import models

# Create your models here.

class File(models.Model):
    FILE_TYPES = [
        ('document', 'Document'),
        ('spreadsheet', 'Spreadsheet'),
        ('presentation', 'Presentation'),
        ('image', 'Image'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='files')
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file = models.FileField(upload_to='project_files/%Y/%m/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.project.title}"

    class Meta:
        ordering = ['-uploaded_at']
