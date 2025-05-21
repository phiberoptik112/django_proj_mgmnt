from django import forms
from .models import File, ProjectMetadata, RoomAcousticsData, Proposal

class RoomAcousticsDataForm(forms.ModelForm):
    class Meta:
        model = RoomAcousticsData
        fields = [
            'project', 
            'room_volume',
            'wall_treatment_materials', 
            'wall_treatment_volume', 
            'ceiling_treatment_materials', 
            'ceiling_treatment_volume', 
            'floor_treatment_materials', 
            'floor_treatment_volume'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'room_volume': forms.NumberInput(attrs={'class': 'form-control'}),
            'wall_treatment_materials': forms.TextInput(attrs={'class': 'form-control'}),
            'wall_treatment_volume': forms.NumberInput(attrs={'class': 'form-control'}),
            'ceiling_treatment_materials': forms.TextInput(attrs={'class': 'form-control'}),
            'ceiling_treatment_volume': forms.NumberInput(attrs={'class': 'form-control'}),
            'floor_treatment_materials': forms.TextInput(attrs={'class': 'form-control'}),
            'floor_treatment_volume': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        exclude = ['project']
        
    def clean(self):
        cleaned_data = super().clean()
        room_volume = cleaned_data.get('room_volume')
        if room_volume is None:
            raise forms.ValidationError("Room volume is required")
        return cleaned_data

class FileForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['title', 'project', 'file_type', 'file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'file_type': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
        }


class ProjectMetadataForm(forms.ModelForm):
    analyze_now = forms.BooleanField(
        required=False, 
        initial=True,
        help_text="Check to analyze the project immediately after saving"
    )
    
    class Meta:
        model = ProjectMetadata
        fields = ['project', 'project_path']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'project_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., /path/to/project/folder'
            }),
        } 

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['project', 'date', 'recipient_name', 'recipient_company', 'recipient_address', 'subject', 'reference', 'introduction', 'basic_services', 'additional_services', 'compensation', 'terms', 'attachments', 'status']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_company': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'introduction': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'basic_services': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'additional_services': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'compensation': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachments': forms.FileInput(attrs={'class': 'form-control'}),
        }
        exclude = ['project']

class ProposalImportForm(forms.Form):
    file = forms.FileField(
        label='Proposal PDF File',
        help_text='Upload a PDF file containing the proposal document.',
        widget=forms.FileInput(attrs={'accept': '.pdf'})
    )
    title = forms.CharField(
        label='Proposal Title',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter a title for this proposal'})
    )
    description = forms.CharField(
        label='Description',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter a description for this proposal'})
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith('.pdf'):
                raise forms.ValidationError('Only PDF files are allowed.')
            if file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError('File size must be less than 10MB.')
        return file