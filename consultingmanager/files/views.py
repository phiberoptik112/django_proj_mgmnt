from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import File, ProjectMetadata, RoomAcousticsData, Email, Proposal, DocumentSummary
from .forms import FileForm, ProjectMetadataForm, RoomAcousticsDataForm, ProposalForm, ProposalImportForm
from .tasks import analyze_project_metadata
from projects.models import Project
from .utils.proposal_parser import ProposalParser
from .utils.pdf_to_markdown import pdf_to_markdown_and_summary
import tempfile
import os
import uuid
from django.conf import settings
from django.apps import apps
from django.db.models import Sum
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.http import require_GET

# Create your views here.

class RoomAcousticsCreateView(LoginRequiredMixin, CreateView):
    model = RoomAcousticsData
    form_class = RoomAcousticsDataForm
    template_name = 'files/room_acoustics_form.html'
    success_url = reverse_lazy('files:file-list')

    def room_acoustics_create(request, project_id):
        project = get_object_or_404(Project, id=project_id)
        if request.method == 'POST':

            form = RoomAcousticsDataForm(request.POST)
            if form.is_valid():
                room_data = form.save(commit=False)
                room_data.project = project
                room_data.save()
                return redirect('files:file-list')
        return render(request, 'files/room_acoustics_form.html', {'form': form})

class FileListView(LoginRequiredMixin, ListView):
    model = File
    template_name = 'files/file_list.html'
    context_object_name = 'files'
    ordering = ['-uploaded_at']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metadata_list'] = ProjectMetadata.objects.all().select_related('project')
        return context

class FileCreateView(LoginRequiredMixin, CreateView):
    model = File
    form_class = FileForm
    template_name = 'files/file_form.html'
    success_url = reverse_lazy('files:file-list')

    def form_valid(self, form):
        messages.success(self.request, 'File uploaded successfully.')
        return super().form_valid(form)

class FileUpdateView(LoginRequiredMixin, UpdateView):
    model = File
    form_class = FileForm
    template_name = 'files/file_form.html'
    success_url = reverse_lazy('files:file-list')

    def form_valid(self, form):
        messages.success(self.request, 'File updated successfully.')
        return super().form_valid(form)

class FileDeleteView(LoginRequiredMixin, DeleteView):
    model = File
    template_name = 'files/file_confirm_delete.html'
    success_url = reverse_lazy('files:file-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'File deleted successfully.')
        return super().delete(request, *args, **kwargs)
    
class FileDetailView(LoginRequiredMixin, DetailView):
    model = File
    template_name = 'files/file_detail.html'
    context_object_name = 'file'

    def post(self, request, *args, **kwargs):
        """Allow triggering PDF -> Markdown processing on this file."""
        self.object = self.get_object()
        action = request.POST.get('action')
        if action == 'process_pdf' and self.object.file and self.object.file.path.lower().endswith('.pdf'):
            try:
                md, summ, page_count, title = pdf_to_markdown_and_summary(self.object.file.path)
                DocumentSummary.objects.create(
                    project=self.object.project,
                    file=self.object,
                    source_path=self.object.file.path,
                    title=title or self.object.title,
                    page_count=page_count,
                    markdown=md,
                    summary=summ,
                    status='processed',
                )
                messages.success(request, 'PDF processed into Markdown and summary.')
            except Exception as e:
                messages.error(request, f'Failed to process PDF: {e}')
        return redirect('files:file-detail', pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document_summaries'] = self.object.document_summaries.all()
        return context

class ProjectMetadataCreateView(LoginRequiredMixin, CreateView):
    model = ProjectMetadata
    form_class = ProjectMetadataForm
    template_name = 'files/metadata_form.html'
    success_url = reverse_lazy('files:file-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data.get('analyze_now'):
            try:
                analyze_project_metadata(self.object.id)
                messages.success(self.request, 'Project metadata created and analysis started.')
            except Exception as e:
                messages.error(self.request, f'Error during analysis: {str(e)}')
        else:
            messages.success(self.request, 'Project metadata created successfully.')
        return response

class ProjectMetadataUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectMetadata
    form_class = ProjectMetadataForm
    template_name = 'files/metadata_form.html'
    success_url = reverse_lazy('files:file-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data.get('analyze_now'):
            try:
                analyze_project_metadata(self.object.id)
                messages.success(self.request, 'Project metadata updated and analysis started.')
            except Exception as e:
                messages.error(self.request, f'Error during analysis: {str(e)}')
        else:
            messages.success(self.request, 'Project metadata updated successfully.')
        return response

class ProposalCreateView(LoginRequiredMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = 'files/proposal_form.html'
    success_url = reverse_lazy('files:proposal-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.all()
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, 'Proposal created successfully.')
            return response
        except Exception as e:
            messages.error(self.request, f'Error creating proposal: {str(e)}')
            return self.form_invalid(form)

class ProposalUpdateView(LoginRequiredMixin, UpdateView):
    model = Proposal
    form_class = ProposalForm
    template_name = 'files/proposal_form.html'
    success_url = reverse_lazy('files:proposal-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.all()
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, 'Proposal updated successfully.')
            return response
        except Exception as e:
            messages.error(self.request, f'Error updating proposal: {str(e)}')
            return self.form_invalid(form)

class ProposalDeleteView(LoginRequiredMixin, DeleteView):
    model = Proposal
    template_name = 'files/proposal_confirm_delete.html'
    success_url = reverse_lazy('files:proposal-list')

    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, 'Proposal deleted successfully.')
            return response
        except Exception as e:
            messages.error(request, f'Error deleting proposal: {str(e)}')
            return redirect('files:proposal-list')

class ProposalDetailView(LoginRequiredMixin, DetailView):
    model = Proposal
    template_name = 'files/proposal_detail.html'
    context_object_name = 'proposal'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

class ProposalImportView(LoginRequiredMixin, View):
    template_name = 'files/proposal_import.html'
    form_class = ProposalImportForm

    def store_temp_proposal(self, pdf_file, prefix='proposal_'):
        """Store uploaded proposal temporarily"""
        os.makedirs(settings.TEMP_PROPOSAL_STORAGE, exist_ok=True)
        
        # Generate unique filename
        filename = f"{prefix}{uuid.uuid4().hex}{os.path.splitext(pdf_file.name)[1]}"
        filepath = os.path.join(settings.TEMP_PROPOSAL_STORAGE, filename)
        
        with open(filepath, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)
        
        return filepath

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        form = self.form_class()
        return render(request, self.template_name, {
            'form': form,
            'project': project
        })

class BulkPdfProcessView(LoginRequiredMixin, View):
    """Process all project PDF `File` records into Markdown summaries."""
    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        processed = 0
        failed = 0
        for f in File.objects.filter(project=project, file_type='document'):
            try:
                if f.file and f.file.path.lower().endswith('.pdf'):
                    md, summ, page_count, title = pdf_to_markdown_and_summary(f.file.path)
                    DocumentSummary.objects.create(
                        project=project,
                        file=f,
                        source_path=f.file.path,
                        title=title or f.title,
                        page_count=page_count,
                        markdown=md,
                        summary=summ,
                        status='processed',
                    )
                    processed += 1
            except Exception:
                failed += 1
                continue
        messages.success(request, f'Processed {processed} PDFs; {failed} failed.')
        return redirect('projects:project-detail', pk=project_id)

@login_required
def analyze_metadata(request, pk):
    """Trigger analysis for a specific project metadata"""
    metadata = get_object_or_404(ProjectMetadata, pk=pk)
    try:
        analyze_project_metadata(metadata.id)
        messages.success(request, 'Analysis completed successfully.')
    except Exception as e:
        messages.error(request, f'Error during analysis: {str(e)}')
    return redirect('files:file-list')

@login_required
def metadata_detail(request, pk):
    """View project metadata details"""
    metadata = get_object_or_404(ProjectMetadata, pk=pk)
    return render(request, 'files/metadata_detail.html', {'metadata': metadata})

@require_GET
def dashboard_project_details(request, project_id):
    """Return project details as JSON for dashboard interactivity."""
    try:
        from billing.models import BillingDetail
    except ImportError:
        BillingDetail = None
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
