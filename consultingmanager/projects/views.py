from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.db.models.functions import TruncWeek
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Project
from .forms import ProjectForm
from django.contrib.auth.mixins import LoginRequiredMixin
from files.models import File
import json
from django.views.decorators.http import require_GET
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.http import JsonResponse
from .forms import ProjectPhaseForm, PhaseWorkLogForm, MilestoneForm, ScopeItemForm
from .models import ProjectPhase, PhaseWorkLog, Milestone, ScopeItem

# Create your views here.

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        status_filter = self.request.GET.get('status', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(client__name__icontains=search_query) |
                Q(client__company__icontains=search_query)
            )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        # Prefetch phases, work logs, and milestones for this project
        return (
            super().get_queryset()
            .select_related('client')
            .prefetch_related(
                'phases',
                'phases__work_logs',
                'milestones',
            )
        )

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:project-list')

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get('client')
        if client_id:
            initial['client'] = client_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Project created successfully.')
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:project-list')

    def form_valid(self, form):
        messages.success(self.request, 'Project updated successfully.')
        return super().form_valid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('projects:project-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Project deleted successfully.')
        return super().delete(request, *args, **kwargs)

class ProjectDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'projects/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all projects with related data
        projects = Project.objects.select_related('client').prefetch_related(
            'files', 'billing_details', 'time_entries', 'metadata'
        )
        
        # Timeline data for chart
        timeline_data = self.get_timeline_data(projects)
        
        # Budget vs actual data
        budget_data = self.get_budget_analysis(projects)
        
        # File activity data
        file_activity = self.get_file_activity_data(projects)
        
        # Project status summary
        status_summary = list(projects.values('status').annotate(
            count=Count('id')
        ).order_by('status'))

        # Prepare status_labels and status_counts for Chart.js
        status_labels = [s['status'].replace('_', ' ').title() for s in status_summary]
        status_counts = [s['count'] for s in status_summary]
        
        context.update({
            'projects': projects,
            'timeline_data': timeline_data,
            'budget_data': budget_data,
            'file_activity_data': file_activity,
            'status_summary': status_summary,
            'status_labels': status_labels,
            'status_counts': status_counts,
            'total_projects': projects.count(),
            'active_projects': projects.filter(
                status__in=['planning', 'in_progress']
            ).count(),
        })
        
        return context
    
    def get_timeline_data(self, projects):
        """Generate timeline data for Gantt-style chart"""
        timeline_data = []
        
        for project in projects:
            # Calculate project duration and progress
            start_date = project.start_date
            end_date = project.end_date or (start_date + timedelta(days=90))  # Default 3 months
            
            # Get file activity dates
            file_dates = list(project.files.values_list('uploaded_at__date', flat=True))
            
            # Get billing dates
            billing_dates = list(project.billing_details.values_list('invoice_date', flat=True))
            
            timeline_data.append({
                'id': project.id,
                'title': project.title,
                'client': project.client.name,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'status': project.status,
                'budget': float(project.budget or 0),
                'file_activity': [d.isoformat() for d in file_dates],
                'billing_activity': [d.isoformat() for d in billing_dates],
            })
            
        return timeline_data
    
    def get_budget_analysis(self, projects):
        """Compare budgets vs actual hours/costs"""
        budget_data = []
        
        for project in projects:
            # Calculate total billed amount
            total_billed = project.billing_details.aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Calculate total hours (if time tracking is implemented)
            total_hours = project.time_entries.aggregate(
                total=Sum('hours')
            )['total'] or 0
            
            budget_data.append({
                'project_id': project.id,
                'title': project.title,
                'budget': float(project.budget or 0),
                'billed': float(total_billed),
                'hours': float(total_hours),
                'budget_utilization': (float(total_billed) / float(project.budget)) * 100 if project.budget else 0,
            })
            
        return budget_data
    
    def get_file_activity_data(self, projects):
        """Get file activity over time"""
        # Group file uploads by week/month

        
        file_activity = []
        
        # Get file uploads grouped by week for the last 6 months
        six_months_ago = timezone.now() - timedelta(days=180)
        
        weekly_uploads = File.objects.filter(
            uploaded_at__gte=six_months_ago
        ).annotate(
            week=TruncWeek('uploaded_at')
        ).values('week', 'project__title').annotate(
            count=Count('id')
        ).order_by('week')
        
        for entry in weekly_uploads:
            file_activity.append({
                'week': entry['week'].isoformat() if entry['week'] else None,
                'project': entry['project__title'],
                'file_count': entry['count'],
            })
            
        return file_activity

@require_GET
def dashboard_project_details(request, project_id):
    """Return project details as JSON for dashboard interactivity."""
    from files.models import File
    try:
        from billing.models import BillingDetail
    except ImportError:
        BillingDetail = None
    from django.apps import apps
    Project = apps.get_model('projects', 'Project')
    project = get_object_or_404(Project, pk=project_id)

    # Status chart (single project)
    status_labels = [project.get_status_display()]
    status_counts = [1]

    # Budget and billed
    budget = project.budget or 0
    # If billing details are related, sum billed for this project
    billed = 0
    if hasattr(project, 'billing_details'):
        billed = project.billing_details.aggregate(total=Sum('amount'))['total'] or 0
    budget_data = [{
        'title': project.title,
        'budget': float(budget),
        'billed': float(billed),
    }]

    # Timeline data (single project)
    timeline_data = [{
        'title': project.title,
        'client': project.client.name if hasattr(project, 'client') else '',
        'status': project.status,
        'start_date': project.start_date.isoformat() if hasattr(project, 'start_date') and project.start_date else '',
        'end_date': project.end_date.isoformat() if hasattr(project, 'end_date') and project.end_date else '',
        'file_activity': list(File.objects.filter(project=project).order_by('uploaded_at').values_list('uploaded_at', flat=True)),
        'billing_activity': list(getattr(project, 'billing_details', []).values_list('date', flat=True)) if hasattr(project, 'billing_details') else [],
    }]

    # File activity data (by week)
    file_qs = File.objects.filter(project=project)
    file_activity_data = []
    for f in file_qs:
        week = f.uploaded_at.strftime('%Y-%W')
        file_activity_data.append({'week': week, 'file_count': 1})

    return JsonResponse({
        'status_labels': status_labels,
        'status_counts': status_counts,
        'budget_data': budget_data,
        'timeline_data': timeline_data,
        'file_activity_data': file_activity_data,
    }, encoder=DjangoJSONEncoder)

class ProjectPhaseCreateView(LoginRequiredMixin, CreateView):
    model = ProjectPhase
    form_class = ProjectPhaseForm
    template_name = 'projects/projectphase_form.html'
    def get_success_url(self):
        return self.object.project.get_absolute_url() if hasattr(self.object.project, 'get_absolute_url') else '/'

class ProjectPhaseUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectPhase
    form_class = ProjectPhaseForm
    template_name = 'projects/projectphase_form.html'
    def get_success_url(self):
        return self.object.project.get_absolute_url() if hasattr(self.object.project, 'get_absolute_url') else '/'

class PhaseWorkLogCreateView(LoginRequiredMixin, CreateView):
    model = PhaseWorkLog
    form_class = PhaseWorkLogForm
    template_name = 'projects/phaseworklog_form.html'
    def get_success_url(self):
        return self.object.phase.project.get_absolute_url() if hasattr(self.object.phase.project, 'get_absolute_url') else '/'

class PhaseWorkLogUpdateView(LoginRequiredMixin, UpdateView):
    model = PhaseWorkLog
    form_class = PhaseWorkLogForm
    template_name = 'projects/phaseworklog_form.html'
    def get_success_url(self):
        return self.object.phase.project.get_absolute_url() if hasattr(self.object.phase.project, 'get_absolute_url') else '/'

class MilestoneCreateView(LoginRequiredMixin, CreateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = 'projects/milestone_form.html'
    def get_success_url(self):
        return self.object.project.get_absolute_url() if hasattr(self.object.project, 'get_absolute_url') else '/'

class MilestoneUpdateView(LoginRequiredMixin, UpdateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = 'projects/milestone_form.html'
    def get_success_url(self):
        return self.object.project.get_absolute_url() if hasattr(self.object.project, 'get_absolute_url') else '/'

def scope_item_detail(request, pk):
    item = get_object_or_404(ScopeItem, pk=pk)
    return render(request, 'projects/scope_detail.html', {'item': item})

def scope_item_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if request.method == 'POST':
        form = ScopeItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('projects:project-detail', pk=project_id)
    else:
        form = ScopeItemForm(initial={'project': project})
    return render(request, 'projects/scope_form.html', {'form': form, 'project': project})