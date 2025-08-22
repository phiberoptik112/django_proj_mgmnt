from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from projects.models import Project, TimeEntry
from clients.models import Client
from files.models import Email, Proposal, FileMetadata
from .models import BillingDetail, ProjectInformationForm, BillingPhase, BillingEmailReference
from .forms import ProjectInformationFormForm, BillingPhaseFormSet

@login_required
def project_billing_dashboard(request, project_id):
    """Main billing dashboard showing PIF data and email timeline"""
    project = get_object_or_404(Project, id=project_id)
    
    # Get PIF data
    try:
        pif = project.pif
    except ProjectInformationForm.DoesNotExist:
        pif = None
    
    # Get all emails with attachments, ordered by date
    emails_with_attachments = Email.objects.filter(
        project=project
    ).prefetch_related(
        'billing_references__billing_detail'
    ).order_by('-date')
    
    # Group emails by month for better timeline display
    email_timeline = {}
    for email in emails_with_attachments:
        month_key = email.date.strftime('%Y-%m')
        if month_key not in email_timeline:
            email_timeline[month_key] = []
        email_timeline[month_key].append(email)
    
    # Get billing summary
    billing_summary = {
        'total_invoiced': BillingDetail.objects.filter(project=project).aggregate(
            total=Sum('amount')
        )['total'] or 0,
        'total_paid': BillingDetail.objects.filter(
            project=project, 
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'outstanding': BillingDetail.objects.filter(
            project=project, 
            status__in=['sent', 'overdue']
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_hours': TimeEntry.objects.filter(project=project).aggregate(
            total=Sum('hours')
        )['total'] or 0,
        'billable_hours': TimeEntry.objects.filter(
            project=project, 
            billable=True
        ).aggregate(total=Sum('hours'))['total'] or 0,
    }
    
    # Calculate PIF totals if available
    pif_totals = None
    if pif and pif.billing_phases.exists():
        pif_totals = {
            'total_amount': pif.billing_phases.aggregate(total=Sum('amount'))['total'] or 0,
            'total_subconsultant_1': pif.billing_phases.aggregate(total=Sum('subconsultant_fee_1'))['total'] or 0,
            'total_subconsultant_2': pif.billing_phases.aggregate(total=Sum('subconsultant_fee_2'))['total'] or 0,
        }
    
    # Get recent proposals
    proposals = Proposal.objects.filter(project=project).order_by('-date')[:5]
    
    context = {
        'project': project,
        'pif': pif,
        'pif_totals': pif_totals,
        'email_timeline': email_timeline,
        'billing_summary': billing_summary,
        'proposals': proposals,
        'billing_details': BillingDetail.objects.filter(project=project).order_by('-invoice_date'),
    }
    
    return render(request, 'billing/project_dashboard.html', context)

@login_required
def pif_create(request, project_id):
    """Create a new PIF for a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        form = ProjectInformationFormForm(request.POST)
        if form.is_valid():
            pif = form.save(commit=False)
            pif.project = project
            pif.save()
            
            # Handle billing phases
            phase_formset = BillingPhaseFormSet(request.POST, instance=pif)
            if phase_formset.is_valid():
                phase_formset.save()
            
            messages.success(request, 'Project Information Form created successfully.')
            return redirect('billing:project_dashboard', project_id=project.id)
    else:
        # Optional prefill from client's billing defaults
        initial = {}
        if request.GET.get('prefill'):
            client = project.client
            initial = {
                'client_name': client.company or client.name,
                'billing_contact': client.billing_contact or client.name,
                'billing_contact_email': client.billing_contact_email or client.email,
                'phone': client.phone,
                'secondary_contact': client.secondary_contact,
                'secondary_contact_email': client.secondary_contact_email,
                'special_negotiated_rates': client.special_negotiated_rates,
                'special_invoice_instructions': client.special_invoice_instructions,
            }
        form = ProjectInformationFormForm(initial=initial)
        phase_formset = BillingPhaseFormSet(instance=None)
    
    context = {
        'project': project,
        'form': form,
        'phase_formset': phase_formset,
        'is_create': True,
    }
    
    return render(request, 'billing/pif_form.html', context)

@login_required
def pif_edit(request, project_id):
    """Edit an existing PIF"""
    project = get_object_or_404(Project, id=project_id)
    
    try:
        pif = project.pif
    except ProjectInformationForm.DoesNotExist:
        messages.error(request, 'No PIF found for this project.')
        return redirect('billing:project_dashboard', project_id=project.id)
    
    if request.method == 'POST':
        form = ProjectInformationFormForm(request.POST, instance=pif)
        if form.is_valid():
            form.save()
            
            # Handle billing phases
            phase_formset = BillingPhaseFormSet(request.POST, instance=pif)
            if phase_formset.is_valid():
                phase_formset.save()
            
            messages.success(request, 'Project Information Form updated successfully.')
            return redirect('billing:project_dashboard', project_id=project.id)
    else:
        form = ProjectInformationFormForm(instance=pif)
        phase_formset = BillingPhaseFormSet(instance=pif)
    
    context = {
        'project': project,
        'pif': pif,
        'form': form,
        'phase_formset': phase_formset,
        'is_create': False,
    }
    
    return render(request, 'billing/pif_form.html', context)

@login_required
def email_detail_modal(request, email_id):
    """AJAX view for displaying email details in modal"""
    email = get_object_or_404(Email, id=email_id)
    
    # Get related billing references
    billing_references = email.billing_references.all()
    
    context = {
        'email': email,
        'billing_references': billing_references,
    }
    
    return render(request, 'billing/email_detail_modal.html', context)

@login_required
@require_http_methods(["POST"])
def link_email_to_billing(request, email_id):
    """Link an email to a billing record"""
    email = get_object_or_404(Email, id=email_id)
    
    try:
        data = json.loads(request.body)
        reference_type = data.get('reference_type')
        billing_detail_id = data.get('billing_detail')
        notes = data.get('notes', '')
        
        if billing_detail_id:
            billing_detail = get_object_or_404(BillingDetail, id=billing_detail_id)
            
            # Create or update the reference
            reference, created = BillingEmailReference.objects.get_or_create(
                email=email,
                billing_detail=billing_detail,
                defaults={
                    'reference_type': reference_type,
                    'notes': notes
                }
            )
            
            if not created:
                reference.reference_type = reference_type
                reference.notes = notes
                reference.save()
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'No billing detail selected'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
