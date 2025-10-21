from django import forms
from django.forms import inlineformset_factory
from .models import ProjectInformationForm, BillingPhase
from clients.models import Client
from .models import PIFScanBatch, PIFScanSchedule
from projects.models import Project

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

class PIFScanBatchForm(forms.ModelForm):
    """Form for creating PIF scan batches"""
    
    class Meta:
        model = PIFScanBatch
        fields = ['name', 'description', 'year_folders']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2023 Projects Scan'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description of what this scan covers'}),
            'year_folders': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': '["/Volumes/KAILUA PROJECTS/2023", "/Volumes/KAILUA PROJECTS/2024"]'
            }),
        }
    
    def clean_year_folders(self):
        """Validate and parse JSON input for year folders"""
        folders_text = self.cleaned_data.get('year_folders')
        if folders_text:
            # If it's already a list (from form processing), return it
            if isinstance(folders_text, list):
                return folders_text
            
            # If it's a string, try to parse as JSON
            if isinstance(folders_text, str):
                try:
                    import json
                    folders = json.loads(folders_text)
                    if not isinstance(folders, list):
                        raise forms.ValidationError("JSON must be an array/list format.")
                    # Validate that all items are strings
                    for i, folder in enumerate(folders):
                        if not isinstance(folder, str):
                            raise forms.ValidationError("All folder paths must be strings.")
                        folders[i] = folder.strip()
                    return folders
                except json.JSONDecodeError:
                    # Fallback: try line-by-line parsing for backward compatibility
                    folders = [folder.strip() for folder in folders_text.split('\n') if folder.strip()]
                    if folders:
                        return folders
                    else:
                        raise forms.ValidationError("Enter a valid JSON array or folder paths.")
        # Require at least one folder
        raise forms.ValidationError("Please provide at least one year folder to scan.")

class PIFScanScheduleForm(forms.ModelForm):
    """Form for creating PIF scan schedules"""
    
    class Meta:
        model = PIFScanSchedule
        fields = ['name', 'description', 'frequency', 'year_folders', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Weekly 2023-2024 Scan'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description of this schedule'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'year_folders': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': '["/Volumes/KAILUA PROJECTS/2023", "/Volumes/KAILUA PROJECTS/2024"]'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_year_folders(self):
        """Validate and parse JSON input for year folders"""
        folders_text = self.cleaned_data.get('year_folders')
        if folders_text:
            # If it's already a list (from form processing), return it
            if isinstance(folders_text, list):
                return folders_text
            
            # If it's a string, try to parse as JSON
            if isinstance(folders_text, str):
                try:
                    import json
                    folders = json.loads(folders_text)
                    if not isinstance(folders, list):
                        raise forms.ValidationError("JSON must be an array/list format.")
                    # Validate that all items are strings
                    for folder in folders:
                        if not isinstance(folder, str):
                            raise forms.ValidationError("All folder paths must be strings.")
                    return folders
                except json.JSONDecodeError:
                    # Fallback: try line-by-line parsing for backward compatibility
                    folders = [folder.strip() for folder in folders_text.split('\n') if folder.strip()]
                    if folders:
                        return folders
                    else:
                        raise forms.ValidationError("Enter a valid JSON array or folder paths.")
        return []

class PIFScanCSVImportForm(forms.Form):
    """Form for importing PIF scan results from CSV"""
    csv_file = forms.FileField(
        label='PIF Scan Results CSV',
        help_text='Upload a CSV file with PIF scan results',
        widget=forms.FileInput(attrs={'accept': '.csv', 'class': 'form-control'})
    )
    batch_name = forms.CharField(
        label='Batch Name',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Imported from CSV'}),
        help_text='Name for this import batch'
    )
    description = forms.CharField(
        label='Description',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description of this import'}),
        help_text='Optional description of this import'
    )
    update_existing = forms.BooleanField(
        label='Update Existing Results',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Update existing scan results if they exist'
    )

    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        if file:
            if not file.name.endswith('.csv'):
                raise forms.ValidationError('Only CSV files are allowed.')
            if file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError('File size must be less than 10MB.')
        return file


class LinkExistingProjectForm(forms.Form):
    """Form to link a scan result to an existing Project."""
    project = forms.ModelChoiceField(
        queryset=Project.objects.all().order_by('-created_at'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label='Select existing project'
    )


class CreateProjectFromScanForm(forms.Form):
    """Form to create a new Project from a scan result."""
    client = forms.ModelChoiceField(
        queryset=Client.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label='Client'
    )
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project title'}),
        required=True,
        label='Project title'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
        required=False,
        label='Description'
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True,
        label='Start date'
    )
    budget = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Budget (optional)'
    )


class CreateClientAndProjectFromScanForm(forms.Form):
    """Form to create both a new Client and a new Project from a scan result."""
    
    # Client fields
    client_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact person name'}),
        required=True,
        label='Client Contact Name'
    )
    client_company = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
        required=True,
        label='Company Name'
    )
    client_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@company.com'}),
        required=True,
        label='Email'
    )
    client_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4567'}),
        required=True,
        label='Phone'
    )
    client_address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Street Address\nCity, State ZIP'}),
        required=True,
        label='Address'
    )
    client_billing_contact = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing contact person (if different)'}),
        required=False,
        label='Billing Contact (optional)'
    )
    client_billing_contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'billing@company.com'}),
        required=False,
        label='Billing Email (optional)'
    )
    
    # Project fields
    project_title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project title'}),
        required=True,
        label='Project Title'
    )
    project_description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
        required=False,
        label='Description'
    )
    project_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True,
        label='Start Date'
    )
    project_budget = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Budget (optional)'
    )
