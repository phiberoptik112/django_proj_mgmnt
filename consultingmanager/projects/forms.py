from django import forms
from .models import Project, ProjectPhase, PhaseWorkLog, Milestone, ScopeItem, RecItem, RecItemVersion, RecItemAttribute

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

class RecItemForm(forms.ModelForm):
    class Meta:
        model = RecItem
        fields = ['scope_item', 'category', 'title', 'description', 'status', 'priority', 'keywords']
        widgets = {
            'scope_item': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'keywords': forms.TextInput(attrs={'class': 'form-control'}),
        }

class RecItemVersionForm(forms.ModelForm):
    class Meta:
        model = RecItemVersion
        fields = ['rec_item', 'version_number', 'title', 'description', 'technical_specs', 'change_source', 'source_file', 'source_email', 'created_by', 'change_notes']
        widgets = {
            'rec_item': forms.Select(attrs={'class': 'form-control'}),
            'version_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'technical_specs': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'change_source': forms.Select(attrs={'class': 'form-control'}),
            'source_file': forms.Select(attrs={'class': 'form-control'}),
            'source_email': forms.Select(attrs={'class': 'form-control'}),
            'created_by': forms.Select(attrs={'class': 'form-control'}),
            'change_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class RecItemAttributeForm(forms.ModelForm):
    class Meta:
        model = RecItemAttribute
        fields = ['rec_item', 'name', 'value', 'unit', 'attribute_type']
        widgets = {
            'rec_item': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'attribute_type': forms.Select(attrs={'class': 'form-control'}),
        } 