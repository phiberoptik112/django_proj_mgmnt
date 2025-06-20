from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import File, ProjectMetadata, RoomAcousticsData, Email, Proposal
from .forms import FileForm, ProjectMetadataForm, RoomAcousticsDataForm, ProposalForm, ProposalImportForm
from .tasks import analyze_project_metadata
from projects.models import Project
from .utils.proposal_parser import ProposalParser
import tempfile
import os
import uuid
from django.conf import settings

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

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Save the uploaded file temporarily
                uploaded_file = request.FILES['file']
                temp_path = self.store_temp_proposal(uploaded_file)

                # Parse the proposal
                parser = ProposalParser(temp_path)
                proposal_data = parser.parse()
                
                # Check for duplicates
                is_duplicate, existing_proposal, file_hash = parser.check_duplicate_by_hash(project_id)
                if is_duplicate:
                    messages.warning(request, f'This proposal appears to be a duplicate of an existing proposal.')
                    os.remove(temp_path)
                    return redirect('projects:project-detail', pk=project_id)

                # Create the proposal
                proposal = Proposal.objects.create(
                    project=project,
                    attachments=uploaded_file,
                    **proposal_data
                )

                # Store file hash
                parser.store_file_hash(proposal, uploaded_file.name)

                # Clean up temporary file
                os.remove(temp_path)

                messages.success(request, 'Proposal imported successfully.')
                return redirect('projects:project-detail', pk=project_id)

            except Exception as e:
                messages.error(request, f'Error importing proposal: {str(e)}')
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return render(request, self.template_name, {
                    'form': form,
                    'project': project
                })

        return render(request, self.template_name, {
            'form': form,
            'project': project
        })

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
