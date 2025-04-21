from django import forms
from .models import File, ProjectMetadata

class FileForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['title', 'project', 'file_type', 'file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'file_type': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
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