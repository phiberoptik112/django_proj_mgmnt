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


# ============================================================================
# Email Timeline Scanner Views
# ============================================================================

from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from .models import EmailScanBatch, EmailTimelineEvent, ProjectStatusIndicator, Email


@login_required
def email_scanner_dashboard(request):
    """Dashboard for email timeline scanning"""
    recent_batches = EmailScanBatch.objects.select_related('project').order_by('-created_at')[:10]
    
    # Statistics
    total_batches = EmailScanBatch.objects.count()
    total_emails_scanned = EmailScanBatch.objects.aggregate(
        total=Sum('total_emails_scanned')
    )['total'] or 0
    total_events = EmailTimelineEvent.objects.count()
    pending_review = EmailTimelineEvent.objects.filter(status='pending').count()
    converted_milestones = EmailTimelineEvent.objects.filter(status='converted').count()
    
    # Recent events needing review
    recent_pending = EmailTimelineEvent.objects.filter(
        status='pending'
    ).select_related('project', 'email').order_by('-created_at')[:10]
    
    context = {
        'recent_batches': recent_batches,
        'recent_pending': recent_pending,
        'stats': {
            'total_batches': total_batches,
            'total_emails_scanned': total_emails_scanned,
            'total_events': total_events,
            'pending_review': pending_review,
            'converted_milestones': converted_milestones,
        }
    }
    return render(request, 'files/email_scanner_dashboard.html', context)


@login_required
def email_scan_batch_create(request):
    """Create a new email scan batch"""
    if request.method == 'POST':
        name = request.POST.get('name', '')
        description = request.POST.get('description', '')
        project_id = request.POST.get('project')
        folder_paths_raw = request.POST.get('folder_paths', '')
        scan_date_from = request.POST.get('scan_date_from') or None
        scan_date_to = request.POST.get('scan_date_to') or None
        
        # Parse folder paths (one per line)
        folder_paths = [p.strip() for p in folder_paths_raw.split('\n') if p.strip()]
        
        # Get project if specified
        project = None
        if project_id:
            project = get_object_or_404(Project, pk=project_id)
        
        # Parse dates
        from datetime import datetime as dt
        if scan_date_from:
            try:
                scan_date_from = dt.strptime(scan_date_from, '%Y-%m-%d').date()
            except ValueError:
                scan_date_from = None
        if scan_date_to:
            try:
                scan_date_to = dt.strptime(scan_date_to, '%Y-%m-%d').date()
            except ValueError:
                scan_date_to = None
        
        batch = EmailScanBatch.objects.create(
            name=name or f"Scan {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            description=description,
            project=project,
            folder_paths=folder_paths,
            scan_date_from=scan_date_from,
            scan_date_to=scan_date_to,
        )
        
        messages.success(request, f'Email scan batch "{batch.name}" created.')
        return redirect('files:email-scan-batch-detail', batch_id=batch.id)
    
    # GET - show form
    projects = Project.objects.all().order_by('title')
    context = {
        'projects': projects,
    }
    return render(request, 'files/email_scan_batch_form.html', context)


@login_required
def email_scan_batch_detail(request, batch_id):
    """View details of an email scan batch"""
    batch = get_object_or_404(EmailScanBatch, id=batch_id)
    
    # Get events for this batch
    events = batch.events.select_related('email', 'project').order_by('-event_date')[:50]
    indicators = batch.indicators.select_related('email', 'project').order_by('-indicator_date')[:20]
    
    context = {
        'batch': batch,
        'events': events,
        'indicators': indicators,
        'stats': batch.get_summary_stats(),
    }
    return render(request, 'files/email_scan_batch_detail.html', context)


@login_required
@require_POST
def run_email_scan_batch(request, batch_id):
    """Run an email scan batch"""
    batch = get_object_or_404(EmailScanBatch, id=batch_id)
    
    if batch.status == 'running':
        messages.warning(request, 'This batch is already running.')
        return redirect('files:email-scan-batch-detail', batch_id=batch.id)
    
    try:
        from .utils.email_scanner import EmailScanner
        scanner = EmailScanner()
        stats = scanner.run_scan_batch(batch.id)
        
        messages.success(
            request, 
            f'Scan completed. Processed {stats["emails_scanned"]} emails, '
            f'found {stats["events_found"]} events.'
        )
    except Exception as e:
        messages.error(request, f'Scan failed: {str(e)}')
    
    return redirect('files:email-scan-batch-detail', batch_id=batch.id)


@login_required
@require_POST
def email_scan_batch_delete(request, batch_id):
    """Delete an email scan batch"""
    batch = get_object_or_404(EmailScanBatch, id=batch_id)
    name = batch.name
    batch.delete()
    messages.success(request, f'Scan batch "{name}" deleted.')
    return redirect('files:email-scanner-dashboard')


@login_required
def email_event_review(request, batch_id=None):
    """Review pending email timeline events"""
    events = EmailTimelineEvent.objects.filter(status='pending').select_related(
        'project', 'email', 'scan_batch'
    ).order_by('-created_at')
    
    if batch_id:
        events = events.filter(scan_batch_id=batch_id)
    
    # Filtering
    project_id = request.GET.get('project')
    event_type = request.GET.get('event_type')
    confidence = request.GET.get('confidence')
    
    if project_id:
        events = events.filter(project_id=project_id)
    if event_type:
        events = events.filter(event_type=event_type)
    if confidence:
        events = events.filter(confidence=confidence)
    
    # Pagination
    paginator = Paginator(events, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'batch_id': batch_id,
        'projects': Project.objects.all(),
        'event_types': EmailTimelineEvent.EVENT_TYPES,
        'confidence_levels': EmailTimelineEvent.CONFIDENCE_LEVELS,
        'filters': {
            'project': project_id,
            'event_type': event_type,
            'confidence': confidence,
        }
    }
    return render(request, 'files/email_event_review.html', context)


@login_required
@require_POST
def confirm_email_event(request, event_id):
    """Confirm an email timeline event"""
    event = get_object_or_404(EmailTimelineEvent, id=event_id)
    
    event.status = 'confirmed'
    event.reviewed_by = request.user
    event.reviewed_at = timezone.now()
    event.review_notes = request.POST.get('notes', '')
    event.save()
    
    messages.success(request, 'Event confirmed.')
    
    # Return to review page or next event
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', ''))
    if next_url:
        return redirect(next_url)
    return redirect('files:email-event-review')


@login_required
@require_POST
def reject_email_event(request, event_id):
    """Reject an email timeline event"""
    event = get_object_or_404(EmailTimelineEvent, id=event_id)
    
    event.status = 'rejected'
    event.reviewed_by = request.user
    event.reviewed_at = timezone.now()
    event.review_notes = request.POST.get('notes', '')
    event.save()
    
    messages.success(request, 'Event rejected.')
    
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', ''))
    if next_url:
        return redirect(next_url)
    return redirect('files:email-event-review')


@login_required
@require_POST
def convert_event_to_milestone(request, event_id):
    """Convert an email timeline event to a project milestone"""
    event = get_object_or_404(EmailTimelineEvent, id=event_id)
    
    if event.milestone:
        messages.warning(request, 'This event has already been converted to a milestone.')
        return redirect('files:email-event-review')
    
    try:
        milestone = event.convert_to_milestone(user=request.user)
        
        # Update batch statistics
        if event.scan_batch:
            event.scan_batch.total_milestones_created += 1
            event.scan_batch.save()
        
        messages.success(request, f'Created milestone: {milestone.name}')
    except Exception as e:
        messages.error(request, f'Failed to create milestone: {str(e)}')
    
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', ''))
    if next_url:
        return redirect(next_url)
    return redirect('files:email-event-review')


@login_required
@require_POST
def bulk_event_action(request):
    """Handle bulk actions on events"""
    action = request.POST.get('action')
    event_ids = request.POST.getlist('event_ids')
    
    if not event_ids:
        messages.warning(request, 'No events selected.')
        return redirect('files:email-event-review')
    
    events = EmailTimelineEvent.objects.filter(id__in=event_ids)
    count = 0
    
    if action == 'confirm':
        for event in events.filter(status='pending'):
            event.status = 'confirmed'
            event.reviewed_by = request.user
            event.reviewed_at = timezone.now()
            event.save()
            count += 1
        messages.success(request, f'{count} events confirmed.')
    
    elif action == 'reject':
        for event in events.filter(status='pending'):
            event.status = 'rejected'
            event.reviewed_by = request.user
            event.reviewed_at = timezone.now()
            event.save()
            count += 1
        messages.success(request, f'{count} events rejected.')
    
    elif action == 'convert':
        for event in events.filter(status__in=['pending', 'confirmed'], milestone__isnull=True):
            try:
                event.convert_to_milestone(user=request.user)
                count += 1
            except Exception as e:
                logger.error(f"Failed to convert event {event.id}: {e}")
        messages.success(request, f'{count} events converted to milestones.')
    
    return redirect('files:email-event-review')


@login_required
def project_email_timeline(request, project_id):
    """View email-derived timeline for a specific project"""
    project = get_object_or_404(Project, id=project_id)
    
    # Get timeline events
    events = EmailTimelineEvent.objects.filter(
        project=project
    ).select_related('email', 'milestone').order_by('event_date')
    
    # Get status indicators
    indicators = ProjectStatusIndicator.objects.filter(
        project=project
    ).select_related('email').order_by('-indicator_date')
    
    # Calculate phase inference
    phase_votes = {}
    for ind in indicators[:20]:
        if ind.inferred_phase:
            phase_votes[ind.inferred_phase] = phase_votes.get(ind.inferred_phase, 0) + 1
    
    current_phase = max(phase_votes, key=phase_votes.get) if phase_votes else 'Unknown'
    
    # Event statistics
    event_stats = {
        'total': events.count(),
        'pending': events.filter(status='pending').count(),
        'confirmed': events.filter(status='confirmed').count(),
        'converted': events.filter(status='converted').count(),
    }
    
    # Upcoming events
    today = timezone.now().date()
    upcoming_events = events.filter(event_date__gte=today).order_by('event_date')[:10]
    past_events = events.filter(event_date__lt=today).order_by('-event_date')[:20]
    
    context = {
        'project': project,
        'events': events,
        'indicators': indicators[:20],
        'current_phase': current_phase,
        'phase_votes': phase_votes,
        'event_stats': event_stats,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
    }
    return render(request, 'files/project_email_timeline.html', context)


@login_required
def quick_project_scan(request, project_id):
    """Quick scan for a single project's emails"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        # Create a batch for this project
        batch = EmailScanBatch.objects.create(
            name=f"Quick scan - {project.title}",
            description=f"Quick scan initiated from project detail page",
            project=project,
        )
        
        try:
            from .utils.email_scanner import EmailScanner
            scanner = EmailScanner()
            stats = scanner.run_scan_batch(batch.id)
            
            messages.success(
                request,
                f'Scan completed. Found {stats["events_found"]} timeline events '
                f'from {stats["emails_scanned"]} emails.'
            )
        except Exception as e:
            messages.error(request, f'Scan failed: {str(e)}')
        
        return redirect('files:project-email-timeline', project_id=project.id)
    
    # GET - show confirmation
    email_count = Email.objects.filter(project=project).count()
    context = {
        'project': project,
        'email_count': email_count,
    }
    return render(request, 'files/quick_project_scan.html', context)


@login_required
def email_event_detail(request, event_id):
    """View details of a single email timeline event"""
    event = get_object_or_404(
        EmailTimelineEvent.objects.select_related('project', 'email', 'scan_batch', 'milestone'),
        id=event_id
    )
    
    context = {
        'event': event,
    }
    return render(request, 'files/email_event_detail.html', context)
