from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Project
from .forms import ProjectForm
from django.contrib.auth.mixins import LoginRequiredMixin

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
