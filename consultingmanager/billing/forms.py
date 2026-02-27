from django import forms
from django.forms import inlineformset_factory
from .models import ProjectInformationForm, BillingPhase
from clients.models import Client
from .models import PIFScanBatch, PIFScanSchedule
from projects.models import Project
import os

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
    """Form for importing PIF scan results from CSV or Excel"""
    csv_file = forms.FileField(
        label='PIF Scan Results File',
        help_text='Upload a CSV (.csv) or Excel (.xlsx) file with PIF scan results',
        widget=forms.FileInput(attrs={'accept': '.csv,.xlsx', 'class': 'form-control'})
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
            # Accept both .csv and .xlsx files
            allowed_extensions = ['.csv', '.xlsx']
            file_ext = os.path.splitext(file.name)[1].lower()

            if file_ext not in allowed_extensions:
                raise forms.ValidationError('Only CSV (.csv) and Excel (.xlsx) files are allowed.')

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


class SinglePIFUploadForm(forms.Form):
    """Form for uploading a single PIF Excel file from home dashboard"""
    pif_file = forms.FileField(
        label='PIF File',
        help_text='Upload a PIF Excel file (.xlsx or .xls)',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls', 'class': 'form-control'})
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all().order_by('-created_at'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Link to Existing Project',
        help_text='Select an existing project or leave blank to create a new one'
    )
    create_new_project = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Create new project from PIF data',
        help_text='If checked, a new project will be created using data from the PIF'
    )

    def clean(self):
        cleaned_data = super().clean()
        pif_file = cleaned_data.get('pif_file')
        project = cleaned_data.get('project')
        create_new = cleaned_data.get('create_new_project')

        # Validate file extension
        if pif_file:
            file_ext = os.path.splitext(pif_file.name)[1].lower()
            if file_ext not in ['.xlsx', '.xls']:
                raise forms.ValidationError('Only Excel files (.xlsx, .xls) are allowed.')

            if pif_file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError('File size must be less than 10MB.')

        # Must select project OR choose to create new
        if not project and not create_new:
            raise forms.ValidationError('Please select an existing project or check "Create new project".')

        # Cannot do both
        if project and create_new:
            raise forms.ValidationError('Please either select an existing project OR create a new one, not both.')

        return cleaned_data


class PIFGeneratorUploadForm(forms.Form):
    """Form for uploading proposal file to generate PIF"""
    proposal_file = forms.FileField(
        label='Proposal File',
        help_text='Upload .doc, .docx, or .txt proposal file',
        widget=forms.FileInput(attrs={
            'accept': '.doc,.docx,.txt',
            'class': 'form-control'
        })
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all().order_by('-created_at'),
        required=False,
        label='Link to Existing Project (Optional)',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Select an existing project to link this PIF to, or leave blank to create a new one'
    )

    def clean_proposal_file(self):
        file = self.cleaned_data.get('proposal_file')
        if file:
            # Validate file extension
            allowed_extensions = ['.doc', '.docx', '.txt']
            file_ext = os.path.splitext(file.name)[1].lower()

            if file_ext not in allowed_extensions:
                raise forms.ValidationError('Only .doc, .docx, and .txt files are allowed.')

            if file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError('File size must be less than 10MB.')

        return file


class PIFGeneratorReviewForm(forms.Form):
    """Form for reviewing and editing extracted PIF fields"""

    # Project Identification
    project_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 24-001'})
    )
    project_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    dlaa_office = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    project_location_city = forms.CharField(
        max_length=100,
        required=False,
        label='City',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    project_location_state = forms.CharField(
        max_length=50,
        required=False,
        label='State',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., HI'})
    )
    originator = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    date_entered = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    # Client Information
    client_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    billing_contact = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    billing_contact_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(808) 555-1234'})
    )
    secondary_contact = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    secondary_contact_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    client_project_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    purchase_order_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # Project Management
    project_manager = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    project_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fee_contract_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    type_of_contract = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Lump Sum'})
    )
    expenses = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    # Special Tax Requirements
    tax_locations = forms.MultipleChoiceField(
        choices=[
            ('hawaii', 'Hawaii'),
            ('oahu', 'Oahu'),
            ('maui', 'Maui'),
            ('kauai', 'Kauai'),
            ('japan', 'Japan'),
            ('south_korea', 'South Korea'),
            ('guam', 'Guam'),
            ('singapore', 'Singapore'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    # Special Billing Information
    special_negotiated_rates = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    special_invoice_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    retainer_received = forms.ChoiceField(
        choices=[('', '---'), ('yes', 'Yes'), ('no', 'No')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    additional_comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def __init__(self, *args, extracted_data=None, confidence_scores=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-fill from extracted_data
        if extracted_data:
            for field, value in extracted_data.items():
                if field in self.fields:
                    self.fields[field].initial = value

        # Add confidence as widget attributes for CSS styling
        if confidence_scores:
            for field, confidence in confidence_scores.items():
                if field in self.fields:
                    self.fields[field].widget.attrs['data-confidence'] = f'{confidence:.2f}'

                    # Add CSS class based on confidence
                    existing_class = self.fields[field].widget.attrs.get('class', '')
                    if confidence >= 0.7:
                        css_class = 'confidence-high'
                    elif confidence >= 0.4:
                        css_class = 'confidence-medium'
                    else:
                        css_class = 'confidence-low'

                    self.fields[field].widget.attrs['class'] = f'{existing_class} {css_class}'.strip()
