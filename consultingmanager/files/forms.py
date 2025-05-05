from django import forms
from .models import File, ProjectMetadata, RoomAcousticsData

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