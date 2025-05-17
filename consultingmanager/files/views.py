from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
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
import os
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

class ProposalImportView(LoginRequiredMixin, FormView):
    form_class = ProposalImportForm
    template_name = 'files/proposal_import.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return context
    
    def form_valid(self, form):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        pdf_file = form.cleaned_data['pdf_file']
        
        try:
            # Save the uploaded file temporarily
            temp_path = os.path.join('/tmp', pdf_file.name)
            with open(temp_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)
            
            # Extract text from PDF
            text = extract_text_from_pdf(temp_path)
            
            # Parse the proposal text
            proposal_data = parse_proposal_text(text)
            
            # Create the proposal
            proposal = Proposal.objects.create(
                project=project,
                date=proposal_data.get('date'),
                recipient_name=proposal_data.get('recipient_name'),
                recipient_company=proposal_data.get('recipient_company'),
                recipient_address=proposal_data.get('recipient_address'),
                subject=proposal_data.get('subject', 'Imported Proposal'),
                introduction=proposal_data.get('introduction', ''),
                basic_services=proposal_data.get('basic_services', []),
                additional_services=proposal_data.get('additional_services', []),
                compensation=proposal_data.get('compensation', {}),
                terms=proposal_data.get('terms', ''),
                status='draft'
            )
            
            # Clean up temporary file
            os.remove(temp_path)
            
            messages.success(self.request, 'Proposal imported successfully.')
            return redirect('files:proposal-detail', pk=proposal.pk)
            
        except Exception as e:
            messages.error(self.request, f'Error importing proposal: {str(e)}')
            return self.form_invalid(form)

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
