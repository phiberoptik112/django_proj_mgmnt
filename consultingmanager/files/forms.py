from django import forms
from .models import File

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