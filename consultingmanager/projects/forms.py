from django import forms
from .models import Project, ProjectPhase, PhaseWorkLog, Milestone, ScopeItem

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'client', 'description', 'start_date', 'end_date', 'status', 'budget']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class ProjectPhaseForm(forms.ModelForm):
    class Meta:
        model = ProjectPhase
        fields = ['name', 'order', 'percent_complete', 'start_date', 'end_date', 'status']

class PhaseWorkLogForm(forms.ModelForm):
    class Meta:
        model = PhaseWorkLog
        fields = ['phase', 'hours_worked', 'hours_invoiced', 'is_wip', 'notes']

class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['name', 'due_date', 'source', 'description', 'related_email']

class ScopeItemForm(forms.ModelForm):
    class Meta:
        model = ScopeItem
        fields = ['project', 'milestone', 'phase', 'category', 'description', 'source_file']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'milestone': forms.Select(attrs={'class': 'form-control'}),
            'phase': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source_file': forms.TextInput(attrs={'class': 'form-control'}),
        } 