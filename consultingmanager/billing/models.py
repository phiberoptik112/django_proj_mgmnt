from django.db import models

# Create your models here.

class BillingDetail(models.Model):
    BILLING_TYPES = [
        ('hourly', 'Hourly Rate'),
        ('fixed', 'Fixed Price'),
        ('milestone', 'Milestone Based'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='billing_details')
    billing_type = models.CharField(max_length=20, choices=BILLING_TYPES)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.project.title}"

    class Meta:
        ordering = ['-invoice_date']
