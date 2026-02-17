from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.urls import reverse_lazy, reverse
from django.db.models.functions import TruncWeek
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import timedelta, datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from .models import Project
from .forms import ProjectForm
from django.contrib.auth.mixins import LoginRequiredMixin
from files.models import File
from clients.models import Client
import json
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.core.serializers.json import DjangoJSONEncoder
from .forms import ProjectPhaseForm, PhaseWorkLogForm, MilestoneForm, ScopeItemForm, RecItemForm, RecItemVersionForm, RecItemAttributeForm
from .models import (
    ProjectPhase, PhaseWorkLog, Milestone, ScopeItem, RecItem, RecItemVersion, 
    RecItemAttribute, ProposalScanResult, ProjectScopeCategory, ProjectTemplate, ActivityLog
)

# Create your views here.

class HomeDashboardView(LoginRequiredMixin, TemplateView):
    """Main home dashboard with key metrics and activity"""
    template_name = 'projects/home_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Project counts by status
        projects = Project.objects.select_related('client')
        context['total_projects'] = projects.count()
        context['active_projects'] = projects.filter(status__in=['planning', 'in_progress']).count()
        context['completed_projects'] = projects.filter(status='completed').count()
        context['on_hold_projects'] = projects.filter(status='on_hold').count()
        
        # Recent projects (last 5)
        context['recent_projects'] = projects.order_by('-updated_at')[:5]
        
        # Upcoming milestones (next 14 days)
        context['upcoming_milestones'] = Milestone.objects.filter(
            due_date__gte=today,
            due_date__lte=today + timedelta(days=14)
        ).select_related('project').order_by('due_date')[:10]
        
        # Overdue milestones
        context['overdue_milestones'] = Milestone.objects.filter(
            due_date__lt=today
        ).select_related('project').order_by('due_date')[:5]
        
        # Recent files (last 10)
        context['recent_files'] = File.objects.select_related('project').order_by('-uploaded_at')[:10]
        
        # Client count
        context['total_clients'] = Client.objects.count()
        
        # Projects by status for chart
        status_data = projects.values('status').annotate(count=Count('id'))
        context['status_labels'] = [s['status'].replace('_', ' ').title() for s in status_data]
        context['status_counts'] = [s['count'] for s in status_data]
        
        # Billing summary (if billing app available)
        try:
            from billing.models import BillingDetail
            context['total_invoiced'] = BillingDetail.objects.filter(
                status__in=['sent', 'paid']
            ).aggregate(total=Sum('amount'))['total'] or 0
            context['total_outstanding'] = BillingDetail.objects.filter(
                status__in=['sent', 'overdue']
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Overdue invoices
            context['overdue_invoices'] = BillingDetail.objects.filter(
                status__in=['sent', 'overdue'],
                due_date__lt=today
            ).select_related('project').order_by('due_date')[:5]
        except ImportError:
            context['total_invoiced'] = 0
            context['total_outstanding'] = 0
            context['overdue_invoices'] = []
        
        return context


@login_required
@require_GET
def global_search(request):
    """Global search endpoint for navbar search"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': {'projects': [], 'clients': [], 'files': []}})
    
    # Search projects
    projects = Project.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(client__name__icontains=query) |
        Q(client__company__icontains=query)
    ).select_related('client')[:10]
    
    project_results = [{
        'id': p.id,
        'title': p.title,
        'client': p.client.company if p.client else '',
        'status': p.get_status_display(),
        'url': reverse('projects:project-detail', kwargs={'pk': p.id})
    } for p in projects]
    
    # Search clients
    clients = Client.objects.filter(
        Q(name__icontains=query) |
        Q(company__icontains=query) |
        Q(email__icontains=query)
    )[:10]
    
    client_results = [{
        'id': c.id,
        'name': c.name,
        'company': c.company,
        'url': reverse('clients:client-detail', kwargs={'pk': c.id})
    } for c in clients]
    
    # Search files
    files = File.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query)
    ).select_related('project')[:10]
    
    file_results = [{
        'id': f.id,
        'title': f.title,
        'project': f.project.title if f.project else '',
        'url': reverse('files:file-detail', kwargs={'pk': f.id})
    } for f in files]
    
    return JsonResponse({
        'results': {
            'projects': project_results,
            'clients': client_results,
            'files': file_results
        }
    })

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        status_filter = self.request.GET.get('status', '')
        scope_category_filter = self.request.GET.get('scope_category', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(client__name__icontains=search_query) |
                Q(client__company__icontains=search_query)
            )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if scope_category_filter:
            queryset = queryset.filter(scope_categories__category_name__icontains=scope_category_filter).distinct()
            
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
        """Generate file activity data for time series chart"""
        file_activity = []
        
        for project in projects:
            # Group files by week
            files_by_week = project.files.annotate(
                week=TruncWeek('uploaded_at')
            ).values('week').annotate(
                file_count=Count('id')
            ).order_by('week')
            
            for week_data in files_by_week:
                file_activity.append({
                    'project_id': project.id,
                    'project_title': project.title,
                    'week': week_data['week'].strftime('%Y-%m-%d'),
                    'file_count': week_data['file_count']
                })
        
        return file_activity

class RecItemDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'projects/recitem_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all RecItems with related data
        rec_items = RecItem.objects.select_related(
            'scope_item', 'scope_item__project', 'scope_item__project__client'
        ).prefetch_related('versions', 'attributes')
        
        # RecItem status distribution
        status_data = self.get_recitem_status_data(rec_items)
        
        # RecItem activity over time
        activity_data = self.get_recitem_activity_data(rec_items)
        
        # RecItem version history
        version_data = self.get_recitem_version_data(rec_items)
        
        # Top projects by RecItem count
        project_data = self.get_project_recitem_data()
        
        # Recent RecItem updates
        recent_updates = self.get_recent_recitem_updates()
        
        context.update({
            'rec_items': rec_items,
            'status_data': status_data,
            'activity_data': activity_data,
            'version_data': version_data,
            'project_data': project_data,
            'recent_updates': recent_updates,
            'total_rec_items': rec_items.count(),
            'total_versions': RecItemVersion.objects.count(),
            'total_projects_with_recitems': Project.objects.filter(
                scope_items__rec_items__isnull=False
            ).distinct().count(),
        })
        
        return context
    
    def get_recitem_status_data(self, rec_items):
        """Get RecItem status distribution for pie chart"""
        status_counts = {}
        
        for rec_item in rec_items:
            status = rec_item.status
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        return {
            'labels': [status.replace('_', ' ').title() for status in status_counts.keys()],
            'data': list(status_counts.values()),
            'colors': ['#28a745', '#007bff', '#ffc107', '#6c757d', '#dc3545']
        }
    
    def get_recitem_activity_data(self, rec_items):
        """Get RecItem activity over time for line chart"""
        activity_by_month = {}
        
        for rec_item in rec_items:
            # Group by month based on latest version date
            latest_version = rec_item.get_latest_version()
            if latest_version:
                month_key = latest_version.created_at.strftime('%Y-%m')
                if month_key not in activity_by_month:
                    activity_by_month[month_key] = 0
                activity_by_month[month_key] += 1
        
        # Sort by month
        sorted_months = sorted(activity_by_month.keys())
        
        return {
            'labels': sorted_months,
            'data': [activity_by_month[month] for month in sorted_months]
        }
    
    def get_recitem_version_data(self, rec_items):
        """Get RecItem version history for bar chart"""
        version_counts = {}
        
        for rec_item in rec_items:
            version_count = rec_item.versions.count()
            if version_count not in version_counts:
                version_counts[version_count] = 0
            version_counts[version_count] += 1
        
        return {
            'labels': [f'{count} versions' for count in sorted(version_counts.keys())],
            'data': [version_counts[count] for count in sorted(version_counts.keys())]
        }
    
    def get_project_recitem_data(self):
        """Get top projects by RecItem count"""
        project_recitem_counts = Project.objects.filter(
            scope_items__rec_items__isnull=False
        ).annotate(
            rec_item_count=Count('scope_items__rec_items')
        ).order_by('-rec_item_count')[:10]
        
        return {
            'labels': [project.title for project in project_recitem_counts],
            'data': [project.rec_item_count for project in project_recitem_counts]
        }
    
    def get_recent_recitem_updates(self):
        """Get recent RecItem updates"""
        return RecItemVersion.objects.select_related(
            'rec_item', 'rec_item__scope_item', 'rec_item__scope_item__project'
        ).order_by('-created_at')[:10]

@require_GET
def dashboard_project_details(request, project_id):
    """AJAX endpoint for getting project-specific dashboard data"""
    project = get_object_or_404(Project, id=project_id)
    
    # Get project-specific data
    timeline_data = []
    start_date = project.start_date
    end_date = project.end_date or (start_date + timedelta(days=90))
    
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
    
    # Budget data
    total_billed = project.billing_details.aggregate(total=Sum('amount'))['total'] or 0
    budget_data = [{
        'project_id': project.id,
        'title': project.title,
        'budget': float(project.budget or 0),
        'billed': float(total_billed),
    }]
    
    # File activity data
    files_by_week = project.files.annotate(
        week=TruncWeek('uploaded_at')
    ).values('week').annotate(
        file_count=Count('id')
    ).order_by('week')
    
    file_activity_data = []
    for week_data in files_by_week:
        file_activity_data.append({
            'project_id': project.id,
            'project_title': project.title,
            'week': week_data['week'].strftime('%Y-%m-%d'),
            'file_count': week_data['file_count']
        })
    
    # Status data (for this project only)
    status_labels = [project.get_status_display()]
    status_counts = [1]
    
    return JsonResponse({
        'timeline_data': timeline_data,
        'budget_data': budget_data,
        'file_activity_data': file_activity_data,
        'status_labels': status_labels,
        'status_counts': status_counts,
    })

@login_required
@require_POST
def analyze_project_recitems(request, project_id):
    """AJAX endpoint to trigger RecItem analysis for a project"""
    try:
        project = get_object_or_404(Project, id=project_id)
        
        # Import here to avoid circular imports
        from files.utils.recitem_analyzer import analyze_project_recitems
        
        # Run the analysis
        results = analyze_project_recitems(project_id)
        
        # Prepare response data
        response_data = {
            'success': True,
            'project_title': project.title,
            'total_updates': results['total_updates'],
            'total_errors': results['total_errors'],
            'analysis_date': results['analysis_date'].isoformat(),
            'message': f"Analysis completed: {results['total_updates']} versions created, {results['total_errors']} errors"
        }
        
        # Add detailed results if requested
        if request.GET.get('detailed') == 'true':
            response_data['email_results'] = [
                {
                    'rec_item_title': r.get('rec_item', {}).title if r.get('rec_item') else 'Unknown',
                    'action': r.get('action'),
                    'error': r.get('error')
                }
                for r in results['email_results']
            ]
            response_data['file_results'] = [
                {
                    'rec_item_title': r.get('rec_item', {}).title if r.get('rec_item') else 'Unknown',
                    'action': r.get('action'),
                    'error': r.get('error')
                }
                for r in results['file_results']
            ]
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f"Analysis failed: {str(e)}"
        }, status=500)

class ProjectPhaseCreateView(LoginRequiredMixin, CreateView):
    model = ProjectPhase
    form_class = ProjectPhaseForm
    template_name = 'projects/projectphase_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:project-detail', kwargs={'pk': self.object.project.pk})

class ProjectPhaseUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectPhase
    form_class = ProjectPhaseForm
    template_name = 'projects/projectphase_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:project-detail', kwargs={'pk': self.object.project.pk})

class PhaseWorkLogCreateView(LoginRequiredMixin, CreateView):
    model = PhaseWorkLog
    form_class = PhaseWorkLogForm
    template_name = 'projects/phaseworklog_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:project-detail', kwargs={'pk': self.object.phase.project.pk})

class PhaseWorkLogUpdateView(LoginRequiredMixin, UpdateView):
    model = PhaseWorkLog
    form_class = PhaseWorkLogForm
    template_name = 'projects/phaseworklog_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:project-detail', kwargs={'pk': self.object.phase.project.pk})

class MilestoneCreateView(LoginRequiredMixin, CreateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = 'projects/milestone_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:project-detail', kwargs={'pk': self.object.project.pk})

class MilestoneUpdateView(LoginRequiredMixin, UpdateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = 'projects/milestone_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:project-detail', kwargs={'pk': self.object.project.pk})

def scope_item_detail(request, pk):
    scope_item = get_object_or_404(ScopeItem, pk=pk)
    return render(request, 'projects/scope_detail.html', {'scope_item': scope_item})

def scope_item_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if request.method == 'POST':
        form = ScopeItemForm(request.POST)
        if form.is_valid():
            scope_item = form.save(commit=False)
            scope_item.project = project
            scope_item.save()
            messages.success(request, 'Scope item created successfully.')
            return redirect('projects:project-detail', pk=project_id)
    else:
        form = ScopeItemForm(initial={'project': project})
    
    return render(request, 'projects/scope_form.html', {'form': form, 'project': project})

# RecItem Views
class RecItemListView(LoginRequiredMixin, ListView):
    model = RecItem
    template_name = 'projects/recitem_list.html'
    context_object_name = 'rec_items'
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        scope_item_id = self.kwargs.get('scope_item_id')
        if scope_item_id:
            queryset = queryset.filter(scope_item_id=scope_item_id)
        return queryset.select_related('scope_item', 'scope_item__project')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scope_item_id = self.kwargs.get('scope_item_id')
        if scope_item_id:
            context['scope_item'] = get_object_or_404(ScopeItem, pk=scope_item_id)
        return context

class RecItemDetailView(LoginRequiredMixin, DetailView):
    model = RecItem
    template_name = 'projects/recitem_detail.html'
    context_object_name = 'rec_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['versions'] = self.object.versions.order_by('-version_number')
        context['attributes'] = self.object.attributes.all()
        return context

class RecItemCreateView(LoginRequiredMixin, CreateView):
    model = RecItem
    form_class = RecItemForm
    template_name = 'projects/recitem_form.html'

    def get_initial(self):
        initial = super().get_initial()
        scope_item_id = self.kwargs.get('scope_item_id')
        if scope_item_id:
            initial['scope_item'] = scope_item_id
        return initial

    def get_success_url(self):
        return reverse_lazy('projects:recitem-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'RecItem created successfully.')
        return super().form_valid(form)

class RecItemUpdateView(LoginRequiredMixin, UpdateView):
    model = RecItem
    form_class = RecItemForm
    template_name = 'projects/recitem_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:recitem-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'RecItem updated successfully.')
        return super().form_valid(form)

class RecItemDeleteView(LoginRequiredMixin, DeleteView):
    model = RecItem
    template_name = 'projects/recitem_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('projects:scope-detail', kwargs={'pk': self.object.scope_item.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'RecItem deleted successfully.')
        return super().delete(request, *args, **kwargs)

# RecItemVersion Views
class RecItemVersionListView(LoginRequiredMixin, ListView):
    model = RecItemVersion
    template_name = 'projects/recitemversion_list.html'
    context_object_name = 'versions'
    ordering = ['-version_number']

    def get_queryset(self):
        rec_item_id = self.kwargs.get('rec_item_id')
        return RecItemVersion.objects.filter(rec_item_id=rec_item_id).select_related('rec_item')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rec_item_id = self.kwargs.get('rec_item_id')
        context['rec_item'] = get_object_or_404(RecItem, pk=rec_item_id)
        return context

class RecItemVersionCreateView(LoginRequiredMixin, CreateView):
    model = RecItemVersion
    form_class = RecItemVersionForm
    template_name = 'projects/recitemversion_form.html'

    def get_initial(self):
        initial = super().get_initial()
        rec_item_id = self.kwargs.get('rec_item_id')
        if rec_item_id:
            rec_item = get_object_or_404(RecItem, pk=rec_item_id)
            initial['rec_item'] = rec_item
            initial['title'] = rec_item.title
            initial['description'] = rec_item.description
            initial['technical_specs'] = rec_item.get_latest_version().technical_specs if rec_item.get_latest_version() else {}
        return initial

    def get_success_url(self):
        return reverse_lazy('projects:recitem-detail', kwargs={'pk': self.object.rec_item.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'New version created successfully.')
        return super().form_valid(form)

# RecItemAttribute Views
class RecItemAttributeCreateView(LoginRequiredMixin, CreateView):
    model = RecItemAttribute
    form_class = RecItemAttributeForm
    template_name = 'projects/recitemattribute_form.html'

    def get_initial(self):
        initial = super().get_initial()
        rec_item_id = self.kwargs.get('rec_item_id')
        if rec_item_id:
            initial['rec_item'] = rec_item_id
        return initial

    def get_success_url(self):
        return reverse_lazy('projects:recitem-detail', kwargs={'pk': self.object.rec_item.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Attribute added successfully.')
        return super().form_valid(form)

class RecItemAttributeUpdateView(LoginRequiredMixin, UpdateView):
    model = RecItemAttribute
    form_class = RecItemAttributeForm
    template_name = 'projects/recitemattribute_form.html'

    def get_success_url(self):
        return reverse_lazy('projects:recitem-detail', kwargs={'pk': self.object.rec_item.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Attribute updated successfully.')
        return super().form_valid(form)

class RecItemAttributeDeleteView(LoginRequiredMixin, DeleteView):
    model = RecItemAttribute
    template_name = 'projects/recitemattribute_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('projects:recitem-detail', kwargs={'pk': self.object.rec_item.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Attribute deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Proposal Scanner Views
class ProposalScanView(LoginRequiredMixin, View):
    """View to scan a project's Business folder for proposal files"""
    
    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        
        # Get project path from metadata
        from projects.utils.proposal_scanner import ProposalScanner
        scanner = ProposalScanner()
        project_path = scanner.get_project_path_from_metadata(project)
        
        if not project_path:
            messages.error(request, 'Project path not found. Please set up project metadata first.')
            return redirect('projects:project-detail', pk=project.pk)
        
        # Scan for proposals
        scan_result = scanner.scan_project_business_folder(project_path)
        
        if scan_result['status'] == 'error':
            messages.error(request, f"Error scanning for proposals: {scan_result['error_message']}")
            return redirect('projects:project-detail', pk=project.pk)
        
        if scan_result['status'] == 'not_found':
            messages.warning(request, 'No proposal files found in Business folder.')
            return redirect('projects:project-detail', pk=project.pk)
        
        # If multiple proposals found, use the first one (most recent)
        proposal_file = scan_result['proposal_files'][0] if scan_result['proposal_files'] else None
        
        if not proposal_file:
            messages.warning(request, 'No proposal files found.')
            return redirect('projects:project-detail', pk=project.pk)
        
        # Parse the proposal
        from projects.utils.proposal_parser import ProposalParser
        parser = ProposalParser(proposal_file)
        parsed_result = parser.parse()
        
        # Create or update scan result
        scan_result_obj, created = ProposalScanResult.objects.update_or_create(
            project=project,
            defaults={
                'proposal_file': proposal_file,
                'raw_text': parsed_result.get('raw_text', ''),
                'status': 'found' if proposal_file else 'not_found',
                'error_message': parsed_result.get('error', ''),
            }
        )
        
        # Redirect to scan result detail page
        return redirect('projects:proposal-scan-result', pk=scan_result_obj.pk)

class ProposalScanResultView(LoginRequiredMixin, DetailView):
    """View to display proposal scan results with raw text and categorized scope"""
    model = ProposalScanResult
    template_name = 'projects/proposal_scan_result.html'
    context_object_name = 'scan_result'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scan_result = self.object
        
        # Parse the proposal to get categories
        from projects.utils.proposal_parser import ProposalParser
        parser = ProposalParser(scan_result.proposal_file)
        parsed_result = parser.parse()
        
        context['raw_text'] = parsed_result.get('raw_text', '')
        context['structure'] = parsed_result.get('structure', {})
        context['detected_categories'] = parsed_result.get('categories', [])
        
        # Get existing categories for this project
        context['existing_categories'] = ProjectScopeCategory.objects.filter(
            project=scan_result.project
        ).values_list('category_name', flat=True)
        
        return context

class ApplyCategoriesView(LoginRequiredMixin, View):
    """View to apply selected categories to project"""
    
    def post(self, request, scan_result_id):
        scan_result = get_object_or_404(ProposalScanResult, pk=scan_result_id)
        project = scan_result.project
        
        # Get selected categories from form
        selected_categories = request.POST.getlist('categories')
        
        if not selected_categories:
            messages.warning(request, 'No categories selected.')
            return redirect('projects:proposal-scan-result', pk=scan_result.pk)
        
        # Parse proposal again to get category details
        from projects.utils.proposal_parser import ProposalParser
        parser = ProposalParser(scan_result.proposal_file)
        parsed_result = parser.parse()
        
        detected_categories = {cat['category_name']: cat for cat in parsed_result.get('categories', [])}
        
        # Create or update ProjectScopeCategory records
        created_count = 0
        updated_count = 0
        
        for category_name in selected_categories:
            category_data = detected_categories.get(category_name, {})
            category_obj, created = ProjectScopeCategory.objects.update_or_create(
                project=project,
                category_name=category_name,
                defaults={
                    'confidence_score': category_data.get('confidence_score', 0.0),
                    'source_file': scan_result.proposal_file,
                    'scan_result': scan_result,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        if created_count > 0:
            messages.success(request, f'Successfully added {created_count} scope categor{"y" if created_count == 1 else "ies"}.')
        if updated_count > 0:
            messages.info(request, f'Updated {updated_count} existing categor{"y" if updated_count == 1 else "ies"}.')
        
        return redirect('projects:project-detail', pk=project.pk)


# Duplicate Project View
@login_required
@require_POST
def duplicate_project(request, project_id):
    """Duplicate a project with optional copying of phases, milestones, and scope items"""
    original_project = get_object_or_404(Project, pk=project_id)
    
    # Get options from POST
    copy_phases = request.POST.get('copy_phases') == 'on'
    copy_milestones = request.POST.get('copy_milestones') == 'on'
    copy_scope = request.POST.get('copy_scope') == 'on'
    new_title = request.POST.get('new_title', f"{original_project.title} (Copy)")
    new_start_date = request.POST.get('new_start_date')
    
    from datetime import datetime
    
    # Parse new start date or use today
    if new_start_date:
        try:
            start_date = datetime.strptime(new_start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = timezone.now().date()
    else:
        start_date = timezone.now().date()
    
    # Calculate date offset
    date_offset = start_date - original_project.start_date
    
    # Create new project
    new_project = Project.objects.create(
        title=new_title,
        client=original_project.client,
        description=original_project.description,
        start_date=start_date,
        end_date=original_project.end_date + date_offset if original_project.end_date else None,
        status='planning',
        budget=original_project.budget
    )
    
    # Copy phases
    if copy_phases:
        for phase in original_project.phases.all():
            ProjectPhase.objects.create(
                project=new_project,
                name=phase.name,
                order=phase.order,
                percent_complete=0,
                start_date=phase.start_date + date_offset if phase.start_date else None,
                end_date=phase.end_date + date_offset if phase.end_date else None,
                status='not_started'
            )
    
    # Copy milestones
    if copy_milestones:
        for milestone in original_project.milestones.all():
            Milestone.objects.create(
                project=new_project,
                name=milestone.name,
                due_date=milestone.due_date + date_offset,
                source='manual',
                description=milestone.description
            )
    
    # Copy scope categories
    if copy_scope:
        for category in original_project.scope_categories.all():
            ProjectScopeCategory.objects.create(
                project=new_project,
                category_name=category.category_name,
                confidence_score=category.confidence_score
            )
    
    # Log activity
    from .models import ActivityLog
    ActivityLog.objects.create(
        project=new_project,
        user=request.user,
        action='create',
        description=f'Duplicated from project "{original_project.title}"',
        object_type='Project',
        object_id=new_project.id,
        metadata={'source_project_id': original_project.id}
    )
    
    messages.success(request, f'Successfully duplicated project as "{new_title}"')
    return redirect('projects:project-detail', pk=new_project.pk)


# Export Projects to Excel
@login_required
def export_projects_excel(request):
    """Export project list to Excel file"""
    import io
    from django.http import HttpResponse
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    
    # Build queryset
    projects = Project.objects.select_related('client').prefetch_related('phases', 'milestones')
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    if client_filter:
        projects = projects.filter(client_id=client_filter)
    
    # Create Excel file using pandas
    import pandas as pd
    
    data = []
    for project in projects:
        # Calculate phase completion
        phases = project.phases.all()
        avg_completion = sum(p.percent_complete for p in phases) / len(phases) if phases else 0
        
        data.append({
            'Project Title': project.title,
            'Client': project.client.company if project.client else '',
            'Status': project.get_status_display(),
            'Start Date': project.start_date,
            'End Date': project.end_date,
            'Budget': float(project.budget) if project.budget else 0,
            'Completion %': round(avg_completion, 1),
            'Total Phases': phases.count(),
            'Total Milestones': project.milestones.count(),
            'Created': project.created_at.strftime('%Y-%m-%d'),
            'Updated': project.updated_at.strftime('%Y-%m-%d'),
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Projects', index=False)
    output.seek(0)
    
    # Create response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.xlsx'
    )
    response['Content-Disposition'] = f'attachment; filename="projects_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    return response


# Quick Time Entry
@login_required
@require_POST
def quick_time_entry(request, project_id):
    """Quick add time entry from project detail page"""
    project = get_object_or_404(Project, pk=project_id)
    
    from .models import TimeEntry
    
    hours = request.POST.get('hours')
    description = request.POST.get('description', '')
    date_str = request.POST.get('date')
    billable = request.POST.get('billable') == 'on'
    
    if not hours:
        messages.error(request, 'Hours are required.')
        return redirect('projects:project-detail', pk=project.pk)
    
    try:
        hours = float(hours)
    except ValueError:
        messages.error(request, 'Invalid hours value.')
        return redirect('projects:project-detail', pk=project.pk)
    
    # Parse date
    from datetime import datetime
    if date_str:
        try:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            entry_date = timezone.now().date()
    else:
        entry_date = timezone.now().date()
    
    # Create time entry
    TimeEntry.objects.create(
        project=project,
        user=request.user,
        date=entry_date,
        hours=hours,
        description=description,
        billable=billable
    )
    
    messages.success(request, f'Added {hours} hours to project.')
    return redirect('projects:project-detail', pk=project.pk)


# Project Templates Views
class ProjectTemplateListView(LoginRequiredMixin, ListView):
    model = ProjectTemplate
    template_name = 'projects/template_list.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        return ProjectTemplate.objects.filter(is_active=True)


class ProjectTemplateCreateView(LoginRequiredMixin, CreateView):
    model = ProjectTemplate
    template_name = 'projects/template_form.html'
    fields = ['name', 'description', 'default_phases', 'default_milestones', 
              'default_scope_categories', 'estimated_duration_days', 'is_active']
    success_url = reverse_lazy('projects:template-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Project template created successfully.')
        return super().form_valid(form)


class ProjectTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectTemplate
    template_name = 'projects/template_form.html'
    fields = ['name', 'description', 'default_phases', 'default_milestones', 
              'default_scope_categories', 'estimated_duration_days', 'is_active']
    success_url = reverse_lazy('projects:template-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Project template updated successfully.')
        return super().form_valid(form)


@login_required
@require_POST
def apply_template_to_project(request, project_id, template_id):
    """Apply a project template to an existing project"""
    project = get_object_or_404(Project, pk=project_id)
    template = get_object_or_404(ProjectTemplate, pk=template_id)
    
    template.apply_to_project(project)
    
    messages.success(request, f'Applied template "{template.name}" to project.')
    return redirect('projects:project-detail', pk=project.pk)


# Activity Log View
class ActivityLogView(LoginRequiredMixin, ListView):
    model = ActivityLog
    template_name = 'projects/activity_log.html'
    context_object_name = 'activities'
    paginate_by = 50
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        if project_id:
            return ActivityLog.objects.filter(project_id=project_id).select_related('project', 'user')
        return ActivityLog.objects.all().select_related('project', 'user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        if project_id:
            context['project'] = get_object_or_404(Project, pk=project_id)
        return context


class BudgetBurnDownView(LoginRequiredMixin, DetailView):
    """Project budget burn-down visualization"""
    model = Project
    template_name = 'projects/budget_burndown.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        
        # Get budget info
        budget = float(project.budget or 0)
        context['budget'] = budget
        
        # Calculate labor costs from time entries
        time_entries = project.time_entries.order_by('date')
        
        # Get staff rates for cost calculation
        labor_data = []
        cumulative_labor = 0
        
        for entry in time_entries:
            # Try to get staff rate, default to $150/hr
            hourly_rate = 150
            try:
                from resources.models import StaffMember
                staff = StaffMember.objects.filter(user=entry.user).first()
                if staff and staff.internal_cost_rate:
                    hourly_rate = float(staff.internal_cost_rate)
            except:
                pass
            
            cost = float(entry.hours) * hourly_rate
            cumulative_labor += cost
            labor_data.append({
                'date': entry.date.isoformat(),
                'hours': float(entry.hours),
                'cost': cost,
                'cumulative': cumulative_labor,
                'description': entry.description[:50] if entry.description else ''
            })
        
        context['labor_data'] = labor_data
        context['total_labor_cost'] = cumulative_labor
        
        # Get expenses
        expense_data = []
        cumulative_expenses = 0
        try:
            from billing.models import Expense
            expenses = Expense.objects.filter(project=project, status='approved').order_by('expense_date')
            for expense in expenses:
                cumulative_expenses += float(expense.amount)
                expense_data.append({
                    'date': expense.expense_date.isoformat(),
                    'amount': float(expense.amount),
                    'cumulative': cumulative_expenses,
                    'category': expense.get_category_display(),
                    'description': expense.description[:50] if expense.description else ''
                })
        except:
            pass
        
        context['expense_data'] = expense_data
        context['total_expenses'] = cumulative_expenses
        
        # Build burn-down chart data (combines labor + expenses)
        all_costs = []
        
        # Merge labor and expense data by date
        for item in labor_data:
            all_costs.append({
                'date': item['date'],
                'amount': item['cost'],
                'type': 'labor'
            })
        
        for item in expense_data:
            all_costs.append({
                'date': item['date'],
                'amount': item['amount'],
                'type': 'expense'
            })
        
        # Sort by date and calculate cumulative
        all_costs.sort(key=lambda x: x['date'])
        
        burn_down_data = []
        remaining = budget
        cumulative_spent = 0
        
        for cost in all_costs:
            cumulative_spent += cost['amount']
            remaining = budget - cumulative_spent
            burn_down_data.append({
                'date': cost['date'],
                'spent': cumulative_spent,
                'remaining': remaining,
                'type': cost['type']
            })
        
        context['burn_down_data'] = json.dumps(burn_down_data, cls=DjangoJSONEncoder)
        context['total_spent'] = cumulative_spent
        context['remaining_budget'] = budget - cumulative_spent
        context['budget_percent_used'] = (cumulative_spent / budget * 100) if budget > 0 else 0
        
        # Budget health status
        if budget > 0:
            percent_used = cumulative_spent / budget * 100
            if percent_used > 100:
                context['budget_status'] = 'over_budget'
                context['budget_status_class'] = 'danger'
            elif percent_used > 90:
                context['budget_status'] = 'critical'
                context['budget_status_class'] = 'warning'
            elif percent_used > 75:
                context['budget_status'] = 'caution'
                context['budget_status_class'] = 'info'
            else:
                context['budget_status'] = 'healthy'
                context['budget_status_class'] = 'success'
        else:
            context['budget_status'] = 'no_budget'
            context['budget_status_class'] = 'secondary'
        
        # Invoice data
        try:
            from billing.models import BillingDetail
            invoices = BillingDetail.objects.filter(project=project).order_by('invoice_date')
            invoice_data = []
            total_invoiced = 0
            total_paid = 0
            
            for inv in invoices:
                total_invoiced += float(inv.amount)
                if inv.status == 'paid':
                    total_paid += float(inv.amount)
                invoice_data.append({
                    'number': inv.invoice_number,
                    'date': inv.invoice_date.isoformat() if inv.invoice_date else '',
                    'amount': float(inv.amount),
                    'status': inv.get_status_display()
                })
            
            context['invoice_data'] = invoice_data
            context['total_invoiced'] = total_invoiced
            context['total_paid'] = total_paid
            context['outstanding'] = total_invoiced - total_paid
        except:
            context['invoice_data'] = []
            context['total_invoiced'] = 0
            context['total_paid'] = 0
            context['outstanding'] = 0
        
        # Profitability
        context['gross_margin'] = context['total_invoiced'] - cumulative_spent
        if context['total_invoiced'] > 0:
            context['margin_percent'] = (context['gross_margin'] / context['total_invoiced']) * 100
        else:
            context['margin_percent'] = 0
        
        return context


@login_required
def budget_burndown_api(request, project_id):
    """API endpoint for budget burn-down data (for AJAX updates)"""
    project = get_object_or_404(Project, pk=project_id)
    
    budget = float(project.budget or 0)
    
    # Get time entry costs
    time_entries = project.time_entries.order_by('date')
    cumulative_cost = 0
    data_points = []
    
    for entry in time_entries:
        hourly_rate = 150
        try:
            from resources.models import StaffMember
            staff = StaffMember.objects.filter(user=entry.user).first()
            if staff and staff.internal_cost_rate:
                hourly_rate = float(staff.internal_cost_rate)
        except:
            pass
        
        cost = float(entry.hours) * hourly_rate
        cumulative_cost += cost
        data_points.append({
            'date': entry.date.isoformat(),
            'spent': cumulative_cost,
            'remaining': budget - cumulative_cost
        })
    
    # Add expenses
    try:
        from billing.models import Expense
        expenses = Expense.objects.filter(project=project, status='approved').order_by('expense_date')
        for expense in expenses:
            cumulative_cost += float(expense.amount)
            data_points.append({
                'date': expense.expense_date.isoformat(),
                'spent': cumulative_cost,
                'remaining': budget - cumulative_cost
            })
    except:
        pass
    
    # Sort by date
    data_points.sort(key=lambda x: x['date'])
    
    return JsonResponse({
        'budget': budget,
        'total_spent': cumulative_cost,
        'remaining': budget - cumulative_cost,
        'data_points': data_points
    })
