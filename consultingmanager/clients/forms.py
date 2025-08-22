from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'name', 'company', 'email', 'phone', 'address',
            'billing_contact', 'billing_contact_email',
            'secondary_contact', 'secondary_contact_email',
            'special_negotiated_rates', 'special_invoice_instructions',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'billing_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'secondary_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'special_negotiated_rates': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'special_invoice_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        } 