from django import forms
from django.forms import inlineformset_factory
from .models import ProjectInformationForm, BillingPhase
from clients.models import Client

class ProjectInformationFormForm(forms.ModelForm):
    """Form for Project Information Form data entry"""
    
    class Meta:
        model = ProjectInformationForm
        fields = [
            'project_number', 'project_name', 'dlaa_office', 
            'project_location_city', 'project_location_state', 'originator', 'date_entered',
            'client_name', 'billing_contact', 'billing_contact_email', 
            'client_project_name', 'purchase_order_number', 'phone',
            'secondary_contact', 'secondary_contact_email',
            'project_manager', 'project_start_date', 'fee_contract_amount', 
            'type_of_contract', 'expenses',
            'tax_locations', 'special_negotiated_rates', 'special_invoice_instructions',
            'retainer_received', 'additional_comments'
        ]
        widgets = {
            'date_entered': forms.DateInput(attrs={'type': 'date'}),
            'project_start_date': forms.DateInput(attrs={'type': 'date'}),
            'fee_contract_amount': forms.NumberInput(attrs={'step': '0.01'}),
            'expenses': forms.NumberInput(attrs={'step': '0.01'}),
            'tax_locations': forms.CheckboxSelectMultiple(),
            'special_invoice_instructions': forms.Textarea(attrs={'rows': 4}),
            'additional_comments': forms.Textarea(attrs={'rows': 4}),
        }

class BillingPhaseForm(forms.ModelForm):
    """Form for individual billing phases"""
    
    class Meta:
        model = BillingPhase
        fields = ['phase_name', 'custom_phase_name', 'max_amount', 'amount', 
                 'subconsultant_fee_1', 'subconsultant_fee_2', 'order']
        widgets = {
            'max_amount': forms.NumberInput(attrs={'step': '0.01'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'subconsultant_fee_1': forms.NumberInput(attrs={'step': '0.01'}),
            'subconsultant_fee_2': forms.NumberInput(attrs={'step': '0.01'}),
            'custom_phase_name': forms.TextInput(attrs={'placeholder': 'Enter custom phase name'}),
        }

# Create formset for billing phases
BillingPhaseFormSet = inlineformset_factory(
    ProjectInformationForm,
    BillingPhase,
    form=BillingPhaseForm,
    extra=1,
    can_delete=True,
    fields=['phase_name', 'custom_phase_name', 'max_amount', 'amount', 
            'subconsultant_fee_1', 'subconsultant_fee_2', 'order']
)


class ClientBillingInstructionsForm(forms.ModelForm):
    """Lightweight form to edit accounting-related client billing instructions."""

    class Meta:
        model = Client
        fields = [
            'accounting_contact_name',
            'accounting_contact_email',
            'invoice_format',
            'special_negotiated_rates',
            'special_invoice_instructions',
        ]
        widgets = {
            'special_negotiated_rates': forms.Textarea(attrs={'rows': 3}),
            'special_invoice_instructions': forms.Textarea(attrs={'rows': 4}),
        }


class ProjectBillingInstructionsForm(forms.ModelForm):
    """Subset of PIF fields commonly needed for invoicing instructions."""

    class Meta:
        model = ProjectInformationForm
        fields = [
            'purchase_order_number',
            'billing_contact',
            'billing_contact_email',
            'special_negotiated_rates',
            'special_invoice_instructions',
        ]
        widgets = {
            'special_negotiated_rates': forms.Textarea(attrs={'rows': 3}),
            'special_invoice_instructions': forms.Textarea(attrs={'rows': 4}),
        }
