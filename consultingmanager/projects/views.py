from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Project
from .forms import ProjectForm
from django.contrib.auth.mixins import LoginRequiredMixin
import json

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
            'timeline_data': json.dumps(timeline_data),
            'budget_data': json.dumps(budget_data),
            'file_activity_data': json.dumps(file_activity),
            'status_summary': status_summary,
            'status_labels': json.dumps(status_labels),
            'status_counts': json.dumps(status_counts),
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
        from django.db.models import TruncWeek
        
        file_activity = []
        
        # Get file uploads grouped by week for the last 6 months
        six_months_ago = timezone.now() - timedelta(days=180)
        
        weekly_uploads = File.objects.filter(
            uploaded_at__gte=six_months_ago
        ).extra(
            select={'week': "date_trunc('week', uploaded_at)"}
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