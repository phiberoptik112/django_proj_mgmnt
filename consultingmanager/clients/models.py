from django.db import models

# Create your models here.

class Client(models.Model):
    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    # Billing-related default contacts for PIF prefill
    billing_contact = models.CharField(max_length=200, blank=True, help_text="Primary billing contact person")
    billing_contact_email = models.EmailField(blank=True, help_text="Billing contact email address")
    secondary_contact = models.CharField(max_length=200, blank=True, help_text="Secondary billing contact")
    secondary_contact_email = models.EmailField(blank=True, help_text="Secondary contact email")
    special_negotiated_rates = models.TextField(blank=True)
    special_invoice_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company}"

    class Meta:
        ordering = ['name']
