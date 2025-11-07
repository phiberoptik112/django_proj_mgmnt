from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Q, F, Value, Count, Max, FloatField, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal
from django.core.paginator import Paginator

from projects.models import Project, TimeEntry
from clients.models import Client
from files.models import Email, Proposal, FileMetadata
from .models import BillingDetail, ProjectInformationForm, BillingPhase, BillingEmailReference, PIFScanBatch, PIFScanSchedule, PIFScanResult
from .forms import (
    ProjectInformationFormForm,
    BillingPhaseFormSet,
    ClientBillingInstructionsForm,
    ProjectBillingInstructionsForm,
    PIFScanBatchForm,
    PIFScanScheduleForm,
    PIFScanCSVImportForm,
    LinkExistingProjectForm,
    CreateProjectFromScanForm,
    CreateClientAndProjectFromScanForm,
)
from .utils.pif_parser import parse_pif_excel
from .utils.volume_access import (
    check_volume_accessible,
    diagnose_file_access,
    refresh_volume_access,
    attempt_volume_reconnection,
)

@staff_member_required
def all_projects_invoicing_summary(request):
    """Accounting-focused summary across all projects with PIF and invoicing aggregates."""
    # Base queryset with joins
    projects_qs = Project.objects.select_related('client').prefetch_related('billing_details', 'phases')

    # Filters (all optional; default all-time)
    client_id = request.GET.get('client')
    status = request.GET.get('status')
    pm = request.GET.get('pm')
    office = request.GET.get('office')
    invoice_status = request.GET.get('invoice_status')
    overdue_only = request.GET.get('overdue') == '1'
    project_type = request.GET.get('project_type')  # placeholder if added later
    keyword = request.GET.get('keyword')

    if client_id:
        projects_qs = projects_qs.filter(client_id=client_id)
    if status:
        projects_qs = projects_qs.filter(status=status)
    if keyword:
        projects_qs = projects_qs.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
    if pm:
        projects_qs = projects_qs.filter(pif__project_manager__icontains=pm)
    if office:
        projects_qs = projects_qs.filter(pif__dlaa_office__icontains=office)

    # Annotate invoice aggregates
    projects_qs = projects_qs.annotate(
        total_invoiced=Coalesce(
            Sum('billing_details__amount', filter=Q(billing_details__status__in=['sent', 'paid'])),
            Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))
        ),
        total_paid=Coalesce(
            Sum('billing_details__amount', filter=Q(billing_details__status='paid')),
            Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))
        ),
        overdue_amount=Coalesce(
            Sum('billing_details__amount', filter=Q(billing_details__status__in=['sent', 'overdue']) & Q(billing_details__due_date__lt=timezone.now().date())),
            Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))
        ),
        overdue_count=Coalesce(
            Count('billing_details__id', filter=Q(billing_details__status__in=['sent', 'overdue']) & Q(billing_details__due_date__lt=timezone.now().date())),
            Value(0)
        ),
        last_invoice_date=Max('billing_details__invoice_date'),
    )

    # Percent complete via phases average (unweighted) as per instruction
    # If weighting is desired later, can align with BillingPhase amounts
    avg_expr = ExpressionWrapper(
        Coalesce(Sum('phases__percent_complete'), Value(0.0)) / Coalesce(Count('phases__id'), Value(1.0)),
        output_field=FloatField()
    )
    projects_qs = projects_qs.annotate(percent_complete=avg_expr)

    # Outstanding definitions
    # 1) Contract outstanding: (contract_amount - paid)
    # 2) Invoiced-but-unpaid: (invoiced - paid)
    projects_qs = projects_qs.annotate(
        contract_amount=Coalesce(F('pif__fee_contract_amount'), F('budget')),  # prefer PIF if present, else project budget
    )
    # Filtering on invoice_status or overdue only
    if invoice_status:
        projects_qs = projects_qs.filter(billing_details__status=invoice_status)
    if overdue_only:
        projects_qs = projects_qs.filter(billing_details__status__in=['sent', 'overdue'], billing_details__due_date__lt=timezone.now().date())

    # Sorting
    order = request.GET.get('order', '-overdue_amount')
    projects_qs = projects_qs.order_by(order)

    # Collect subconsultant totals via PIF billing phases
    # We'll compute per project in Python to avoid heavy joins if needed
    project_rows = []
    projects_list = list(projects_qs.distinct())
    today = timezone.now().date()
    for project in projects_list:
        pif = getattr(project, 'pif', None)
        # Subconsultant totals
        sub1_total = 0
        sub2_total = 0
        contract_amount = None
        office_val = None
        pm_val = None
        po_val = None
        if pif:
            phases = pif.billing_phases.all()
            sub1_total = phases.aggregate(total=Coalesce(
                Sum('subconsultant_fee_1'),
                Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))
            ))['total'] or 0
            sub2_total = phases.aggregate(total=Coalesce(
                Sum('subconsultant_fee_2'),
                Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))
            ))['total'] or 0
            contract_amount = pif.fee_contract_amount
            office_val = pif.dlaa_office
            pm_val = pif.project_manager
            po_val = pif.purchase_order_number
        # Fallbacks
        if contract_amount is None:
            contract_amount = project.budget

        total_invoiced = getattr(project, 'total_invoiced', 0) or 0
        total_paid = getattr(project, 'total_paid', 0) or 0
        invoiced_but_unpaid = (total_invoiced or 0) - (total_paid or 0)
        contract_outstanding = (contract_amount or 0) - (total_paid or 0) if contract_amount is not None else None

        # Last invoice
        last_invoice = project.billing_details.order_by('-invoice_date').first()

        # Mismatch flags
        mismatches = []
        client = project.client
        if pif:
            if client.billing_contact and pif.billing_contact and client.billing_contact != pif.billing_contact:
                mismatches.append('Billing contact differs from Client defaults')
            if client.billing_contact_email and pif.billing_contact_email and client.billing_contact_email != pif.billing_contact_email:
                mismatches.append('Billing contact email differs from Client defaults')
            if client.special_invoice_instructions and pif.special_invoice_instructions and client.special_invoice_instructions != pif.special_invoice_instructions:
                mismatches.append('Invoice instructions differ from Client defaults')
            if contract_amount and project.budget and contract_amount != project.budget:
                mismatches.append('Contract amount differs from Project budget')

        project_rows.append({
            'project': project,
            'client': client,
            'office': office_val,
            'project_manager': pm_val,
            'contract_amount': contract_amount,
            'budget': project.budget,
            'percent_complete': getattr(project, 'percent_complete', 0) or 0,
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'invoiced_but_unpaid': invoiced_but_unpaid,
            'contract_outstanding': contract_outstanding,
            'overdue_amount': getattr(project, 'overdue_amount', 0) or 0,
            'overdue_count': getattr(project, 'overdue_count', 0) or 0,
            'last_invoice': last_invoice,
            'po_number': po_val,
            'subconsultant_fee_1_total': sub1_total,
            'subconsultant_fee_2_total': sub2_total,
            'mismatches': mismatches,
        })

    # Export CSV if requested
    export = request.GET.get('export')
    if export == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="invoicing_summary.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Client', 'Company', 'Project', 'PM', 'Office', 'Status',
            'Contract Amount', 'Budget', '% Complete', 'Invoiced', 'Paid',
            'Invoiced-Unpaid', 'Contract Outstanding', 'Overdue Amount', 'Overdue Count',
            'Last Invoice #', 'Last Invoice Date', 'PO/Client Ref', 'Subconsultant 1', 'Subconsultant 2'
        ])
        for r in project_rows:
            writer.writerow([
                r['client'].name,
                r['client'].company,
                r['project'].title,
                r.get('project_manager') or '',
                r.get('office') or '',
                r['project'].get_status_display(),
                r.get('contract_amount') or 0,
                r.get('budget') or 0,
                round(r.get('percent_complete') or 0, 0),
                r.get('total_invoiced') or 0,
                r.get('total_paid') or 0,
                r.get('invoiced_but_unpaid') or 0,
                r.get('contract_outstanding') if r.get('contract_outstanding') is not None else '',
                r.get('overdue_amount') or 0,
                r.get('overdue_count') or 0,
                (r.get('last_invoice').invoice_number if r.get('last_invoice') else ''),
                (r.get('last_invoice').invoice_date if r.get('last_invoice') else ''),
                r.get('po_number') or '',
                r.get('subconsultant_fee_1_total') or 0,
                r.get('subconsultant_fee_2_total') or 0,
            ])
        return response

    # Filters lists for HTML
    clients = Client.objects.all().order_by('name')
    statuses = Project.STATUS_CHOICES

    context = {
        'rows': project_rows,
        'clients': clients,
        'statuses': statuses,
        'selected': {
            'client': client_id,
            'status': status,
            'pm': pm,
            'office': office,
            'invoice_status': invoice_status,
            'overdue': overdue_only,
            'project_type': project_type,
            'keyword': keyword,
            'order': order,
        },
        # Empty forms for the side panel (bound dynamically via JS)
        'client_form': ClientBillingInstructionsForm(),
        'project_form': ProjectBillingInstructionsForm(),
    }

    return render(request, 'billing/invoicing_summary.html', context)


@login_required
@require_http_methods(["GET"]) 
def get_billing_instructions(request, project_id):
    """Return combined client and project billing instruction fields for a project.
    Used by the summary page panel to populate fields when a project row is selected.
    """
    project = get_object_or_404(Project, id=project_id)
    client = project.client

    pif = getattr(project, 'pif', None)

    data = {
        'client': {
            'id': client.id,
            'name': client.name,
            'company': client.company,
            'accounting_contact_name': client.accounting_contact_name,
            'accounting_contact_email': client.accounting_contact_email,
            'invoice_format': client.invoice_format,
            'special_negotiated_rates': client.special_negotiated_rates,
            'special_invoice_instructions': client.special_invoice_instructions,
        },
        'project': {
            'id': project.id,
            'title': project.title,
            'purchase_order_number': getattr(pif, 'purchase_order_number', ''),
            'billing_contact': getattr(pif, 'billing_contact', ''),
            'billing_contact_email': getattr(pif, 'billing_contact_email', ''),
            'special_negotiated_rates': getattr(pif, 'special_negotiated_rates', ''),
            'special_invoice_instructions': getattr(pif, 'special_invoice_instructions', ''),
        }
    }

    return JsonResponse({'success': True, 'data': data})


@login_required
@require_http_methods(["POST"]) 
def save_billing_instructions(request, project_id):
    """Save client and project-specific billing instruction fields from the panel.
    This endpoint accepts JSON with 'client' and 'project' payloads.
    """
    project = get_object_or_404(Project, id=project_id)
    client = project.client

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)

    client_payload = payload.get('client', {})
    project_payload = payload.get('project', {})

    # Update Client (partial)
    client_form = ClientBillingInstructionsForm(client_payload, instance=client)
    client_ok = client_form.is_valid()

    # Ensure a PIF exists for project fields
    pif = getattr(project, 'pif', None)
    if pif is None:
        pif = ProjectInformationForm.objects.create(project=project)

    project_form = ProjectBillingInstructionsForm(project_payload, instance=pif)
    project_ok = project_form.is_valid()

    if client_ok and project_ok:
        client_form.save()
        project_form.save()
        return JsonResponse({'success': True})

    errors = {
        'client': client_form.errors,
        'project': project_form.errors,
    }
    return JsonResponse({'success': False, 'errors': errors}, status=400)

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

# PIF Scanner Views
@staff_member_required
def pif_scanner_dashboard(request):
    """Main dashboard for PIF scanner management"""
    # Get recent scan batches
    recent_batches = PIFScanBatch.objects.all()[:10]
    
    # Get active schedules
    active_schedules = PIFScanSchedule.objects.filter(is_active=True)
    
    # Get scan statistics
    total_scanned = PIFScanResult.objects.count()
    total_ingested = PIFScanResult.objects.filter(status='ingested').count()
    total_errors = PIFScanResult.objects.filter(status='error').count()
    total_with_project_numbers = PIFScanResult.objects.exclude(project_number='').count()
    total_linked_to_projects = PIFScanResult.objects.exclude(project=None).count()
    
    context = {
        'recent_batches': recent_batches,
        'active_schedules': active_schedules,
        'stats': {
            'total_scanned': total_scanned,
            'total_ingested': total_ingested,
            'total_errors': total_errors,
            'total_with_project_numbers': total_with_project_numbers,
            'total_linked_to_projects': total_linked_to_projects,
            'success_rate': (total_ingested / total_scanned * 100) if total_scanned > 0 else 0,
            'project_number_rate': (total_with_project_numbers / total_scanned * 100) if total_scanned > 0 else 0,
            'project_linking_rate': (total_linked_to_projects / total_with_project_numbers * 100) if total_with_project_numbers > 0 else 0
        }
    }
    
    return render(request, 'billing/pif_scanner_dashboard.html', context)

@staff_member_required
def pif_scan_batch_create(request):
    """Create a new PIF scan batch"""
    if request.method == 'POST':
        form = PIFScanBatchForm(request.POST)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f'Scan batch "{batch.name}" created successfully.')
            return redirect('billing:pif_scan_batch_detail', batch_id=batch.id)
    else:
        form = PIFScanBatchForm()
    
    context = {
        'form': form,
        'is_create': True,
    }
    
    return render(request, 'billing/pif_scan_batch_form.html', context)

@staff_member_required
def pif_scan_batch_detail(request, batch_id):
    """View details of a PIF scan batch"""
    batch = get_object_or_404(PIFScanBatch, id=batch_id)
    scan_results = batch.scan_results.all()[:50]  # Show first 50 results
    
    context = {
        'batch': batch,
        'scan_results': scan_results,
        'stats': batch.get_summary_stats(),
    }
    
    return render(request, 'billing/pif_scan_batch_detail.html', context)

@staff_member_required
@require_http_methods(["POST"]) 
def pif_scan_batch_delete(request, batch_id):
    """Delete a PIF scan batch and its results."""
    batch = get_object_or_404(PIFScanBatch, id=batch_id)
    name = batch.name
    # Cascade delete will remove related PIFScanResult due to FK on_delete=CASCADE
    batch.delete()
    messages.success(request, f'Scan batch "{name}" deleted.')
    return redirect('billing:pif_scanner_dashboard')

@staff_member_required
@require_http_methods(["POST"]) 
def pif_scan_batch_rerun(request, batch_id):
    """Re-run a PIF scan for an existing batch configuration.
    Resets stats and runs the same folders again.
    """
    batch = get_object_or_404(PIFScanBatch, id=batch_id)

    # Guard: ensure batch has configured folders; CSV-imported batches won't
    if not batch.year_folders:
        messages.error(request, 'Cannot re-run this batch: no year folders are configured (likely an imported batch). Create a new batch with folders to scan.')
        return redirect('billing:pif_scan_batch_detail', batch_id=batch.id)

    # Reset statistics and previous results for a clean run
    batch.total_scanned = 0
    batch.total_ingested = 0
    batch.total_skipped = 0
    batch.total_errors = 0
    batch.error_summary = ''
    batch.status = 'running'
    batch.started_at = timezone.now()
    batch.completed_at = None
    batch.save()

    # Delete prior results to avoid duplicates across runs
    batch.scan_results.all().delete()

    try:
        from .utils.pif_scanner import PIFScanner
        scanner = PIFScanner()

        for folder_path in batch.year_folders:
            results = scanner.scan_year_folder(folder_path)
            for result_data in results:
                scan_result = PIFScanResult.objects.create(
                    scan_batch=batch,
                    container_dir=result_data.get('container_dir', ''),
                    folder_kind=result_data.get('folder_kind', ''),
                    pif_file=result_data.get('pif_file', ''),
                    files_count=result_data.get('files_count'),
                    rows=result_data.get('rows'),
                    status=result_data.get('status', 'skipped'),
                    reason=result_data.get('reason', ''),
                )
                scan_result.extract_project_info_from_path()
                scan_result.save()
                scan_result.link_to_project()

        consolidated_count, deleted_count = PIFScanResult.consolidate_duplicates(batch)

        batch.total_scanned = batch.scan_results.count()
        batch.total_ingested = batch.scan_results.filter(status='ingested').count()
        batch.total_skipped = batch.scan_results.filter(status='skipped').count()
        batch.total_errors = batch.scan_results.filter(status='error').count()
        batch.status = 'completed'
        batch.completed_at = timezone.now()
        batch.save()

        if consolidated_count > 0:
            messages.success(request, f'Re-ran "{batch.name}" successfully. Consolidated {consolidated_count} duplicate projects, removed {deleted_count} entries.')
        else:
            messages.success(request, f'Re-ran "{batch.name}" successfully.')
    except Exception as e:
        batch.status = 'failed'
        batch.error_summary = str(e)
        batch.save()
        messages.error(request, f'Re-run failed: {str(e)}')

    return redirect('billing:pif_scan_batch_detail', batch_id=batch.id)

@staff_member_required
def run_pif_scan_batch(request, batch_id):
    """Run a PIF scan batch"""
    batch = get_object_or_404(PIFScanBatch, id=batch_id)
    
    if request.method == 'POST':
        if not batch.year_folders:
            messages.error(request, 'This batch has no year folders configured; nothing to scan.')
            return redirect('billing:pif_scan_batch_detail', batch_id=batch.id)
        # Start the scan process
        batch.status = 'running'
        batch.started_at = timezone.now()
        batch.save()
        
        # In a real implementation, this would be a background task
        # For now, we'll simulate the process
        try:
            # Import and run the scanner
            from .utils.pif_scanner import PIFScanner
            scanner = PIFScanner()
            
            for folder_path in batch.year_folders:
                results = scanner.scan_year_folder(folder_path)
                for result_data in results:
                    # Create scan result
                    scan_result = PIFScanResult.objects.create(
                        scan_batch=batch,
                        container_dir=result_data.get('container_dir', ''),
                        folder_kind=result_data.get('folder_kind', ''),
                        pif_file=result_data.get('pif_file', ''),
                        files_count=result_data.get('files_count'),
                        rows=result_data.get('rows'),
                        status=result_data.get('status', 'skipped'),
                        reason=result_data.get('reason', ''),
                    )
                    scan_result.extract_project_info_from_path()
                    scan_result.save()
                    
                    # Try to automatically link to existing project
                    scan_result.link_to_project()
            
                # Consolidate duplicates
                consolidated_count, deleted_count = PIFScanResult.consolidate_duplicates(batch)
                
                # Update batch statistics
                batch.total_scanned = batch.scan_results.count()
                batch.total_ingested = batch.scan_results.filter(status='ingested').count()
                batch.total_skipped = batch.scan_results.filter(status='skipped').count()
                batch.total_errors = batch.scan_results.filter(status='error').count()
                batch.status = 'completed'
                batch.completed_at = timezone.now()
                batch.save()
                
                if consolidated_count > 0:
                    messages.success(request, f'Scan batch "{batch.name}" completed successfully. Consolidated {consolidated_count} duplicate projects, removed {deleted_count} duplicate entries.')
                else:
                    messages.success(request, f'Scan batch "{batch.name}" completed successfully.')
            
        except Exception as e:
            batch.status = 'failed'
            batch.error_summary = str(e)
            batch.save()
            messages.error(request, f'Scan batch failed: {str(e)}')
    
    return redirect('billing:pif_scan_batch_detail', batch_id=batch.id)

@staff_member_required
def pif_scan_results(request, batch_id):
    """View all results for a scan batch"""
    batch = get_object_or_404(PIFScanBatch, id=batch_id)
    scan_results = batch.scan_results.all()
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        scan_results = scan_results.filter(status=status_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        scan_results = scan_results.filter(
            Q(project_number__icontains=search) |
            Q(project_name__icontains=search) |
            Q(container_dir__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(scan_results, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'batch': batch,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search': search,
    }
    
    return render(request, 'billing/pif_scan_results.html', context)


@staff_member_required
def pif_scan_result_detail(request, result_id):
    """Detail page for a single PIF scan result with actions to link or create a project."""
    result = get_object_or_404(PIFScanResult, id=result_id)
    
    # Parse PIF for preview if available
    parsed = parse_pif_excel(result.pif_file) if result.pif_file else {}
    
    # Build initial data from parsed PIF
    initial_title = result.project_number + ' ' + result.project_name if result.project_number and result.project_name else (result.project_name or '')
    
    # Construct address from parsed fields
    address_parts = []
    if parsed.get('billing_address_line_1'):
        address_parts.append(parsed['billing_address_line_1'])
    if parsed.get('billing_address_line_2'):
        address_parts.append(parsed['billing_address_line_2'])
    
    # Add city, state, zip on one line if available
    city_state_zip = []
    if parsed.get('project_location_city'):
        city_state_zip.append(parsed['project_location_city'])
    if parsed.get('project_location_state'):
        city_state_zip.append(parsed['project_location_state'])
    if parsed.get('billing_zip'):
        city_state_zip.append(parsed['billing_zip'])
    if city_state_zip:
        address_parts.append(', '.join(city_state_zip))
    
    initial_address = '\n'.join(address_parts) if address_parts else ''
    
    # Pre-populate form with parsed data
    link_form = LinkExistingProjectForm()
    create_form = CreateProjectFromScanForm(initial={'title': initial_title})
    create_client_and_project_form = CreateClientAndProjectFromScanForm(initial={
        # Client fields
        'client_name': parsed.get('billing_contact') or '',
        'client_company': parsed.get('client_name') or '',
        'client_email': parsed.get('billing_contact_email') or '',
        'client_phone': parsed.get('phone') or '',
        'client_address': initial_address,
        'client_billing_contact': parsed.get('billing_contact') or '',
        'client_billing_contact_email': parsed.get('billing_contact_email') or '',
        # Project fields
        'project_title': initial_title,
        'project_start_date': parsed.get('project_start_date') or '',
        'project_budget': parsed.get('fee_contract_amount') or parsed.get('project_budget') or '',
    })
    pif_preview = {
        'pif_file': result.pif_file,
        'rows': result.rows,
        'project_number': parsed.get('project_number') or result.project_number,
        'project_name': parsed.get('project_name') or result.project_name,
        'container_dir': result.container_dir,
        'status': result.status,
        'reason': result.reason,
        'client_name': parsed.get('client_name'),
        'project_manager': parsed.get('project_manager'),
        'fee_contract_amount': parsed.get('fee_contract_amount'),
        'purchase_order_number': parsed.get('purchase_order_number'),
        'billing_contact': parsed.get('billing_contact'),
        'billing_contact_email': parsed.get('billing_contact_email'),
        'dlaa_office': parsed.get('dlaa_office'),
        'project_location_city': parsed.get('project_location_city'),
        'project_location_state': parsed.get('project_location_state'),
        'project_start_date': parsed.get('project_start_date'),
        'expenses': parsed.get('expenses'),
        'type_of_contract': parsed.get('type_of_contract'),
        'tax_locations': parsed.get('tax_locations'),
        'retainer_received': parsed.get('retainer_received'),
    }

    # If linked to a project, prepare client/budget/phase summaries
    linked = None
    if result.project:
        project = result.project
        linked_pif = getattr(project, 'pif', None)
        phases_count = 0
        amount_total = 0
        sub1_total = 0
        sub2_total = 0
        fee_contract_amount = None
        if linked_pif:
            phases_count = linked_pif.billing_phases.count()
            fee_contract_amount = linked_pif.fee_contract_amount
            amount_total = linked_pif.billing_phases.aggregate(total=Sum('amount'))['total'] or 0
            sub1_total = linked_pif.billing_phases.aggregate(total=Sum('subconsultant_fee_1'))['total'] or 0
            sub2_total = linked_pif.billing_phases.aggregate(total=Sum('subconsultant_fee_2'))['total'] or 0
        linked = {
            'project_title': project.title,
            'client_name': project.client.name,
            'client_company': project.client.company,
            'budget': project.budget,
            'pif_fee_contract_amount': fee_contract_amount,
            'phases_count': phases_count,
            'phases_amount_total': amount_total,
            'sub1_total': sub1_total,
            'sub2_total': sub2_total,
        }

    # Add volume diagnostics if file path exists
    volume_diagnostics = None
    if result.pif_file:
        file_check = check_volume_accessible(result.pif_file)
        if not file_check.get('accessible'):
            volume_diagnostics = diagnose_file_access(result.pif_file)

    context = {
        'result': result,
        'link_form': link_form,
        'create_form': create_form,
        'create_client_and_project_form': create_client_and_project_form,
        'pif_preview': pif_preview,
        'parsed': parsed,
        'linked': linked,
        'volume_diagnostics': volume_diagnostics,
        'file_check': check_volume_accessible(result.pif_file) if result.pif_file else None,
    }
    return render(request, 'billing/pif_scan_result_detail.html', context)


@staff_member_required
@require_http_methods(["POST"])
def pif_refresh_volume_access(request, result_id):
    """Refresh volume access for a PIF scan result."""
    result = get_object_or_404(PIFScanResult, id=result_id)
    
    if not result.pif_file:
        messages.error(request, 'No PIF file path associated with this result.')
        return redirect('billing:pif_scan_result_detail', result_id=result.id)
    
    # Get volume information
    file_check = check_volume_accessible(result.pif_file)
    volume_name = file_check.get('volume_name')
    
    if not volume_name:
        messages.warning(request, 'Could not determine volume name from file path.')
        return redirect('billing:pif_scan_result_detail', result_id=result.id)
    
    # Attempt to refresh/reconnect
    reconnect_result = attempt_volume_reconnection(volume_name)
    
    if reconnect_result['success']:
        messages.success(request, f"✓ {reconnect_result['best_message']}")
    else:
        messages.warning(request, f"⚠ {reconnect_result['best_message']}")
        messages.info(request, 'Try disconnecting and reconnecting the volume in Finder (Cmd+K).')
    
    return redirect('billing:pif_scan_result_detail', result_id=result.id)


@staff_member_required
@require_http_methods(["POST"])
def pif_link_to_existing_project(request, result_id):
    """Link a scan result to an existing Project and optionally update the result's project fields."""
    result = get_object_or_404(PIFScanResult, id=result_id)
    form = LinkExistingProjectForm(request.POST)
    if form.is_valid():
        project = form.cleaned_data['project']
        result.project = project
        result.save()

        # Optionally write parsed PIF fields to project's PIF and budget
        if 'save_pif' in request.POST and result.pif_file:
            parsed = parse_pif_excel(result.pif_file) or {}
            if parsed:
                pif, _ = ProjectInformationForm.objects.get_or_create(project=project)
                field_names = [f.name for f in ProjectInformationForm._meta.fields if f.name not in ('id', 'project')]
                for key, val in parsed.items():
                    if key in field_names:
                        setattr(pif, key, val)
                # Ensure number/name present at minimum
                if not parsed.get('project_number') and result.project_number:
                    pif.project_number = result.project_number
                if not parsed.get('project_name') and result.project_name:
                    pif.project_name = result.project_name
                pif.save()

                if parsed.get('project_budget') is not None:
                    project.budget = parsed['project_budget']
                    project.save()
        messages.success(request, 'Linked scan result to existing project.')
        return redirect('billing:pif_scan_result_detail', result_id=result.id)
    messages.error(request, 'Please select a valid project.')
    return redirect('billing:pif_scan_result_detail', result_id=result.id)


@staff_member_required
@require_http_methods(["POST"])
def pif_create_project_from_result(request, result_id):
    """Create a new Project from the scan result and link it, optionally create an empty PIF record."""
    result = get_object_or_404(PIFScanResult, id=result_id)
    form = CreateProjectFromScanForm(request.POST)
    if form.is_valid():
        client = form.cleaned_data['client']
        title = form.cleaned_data['title']
        description = form.cleaned_data.get('description') or ''
        start_date = form.cleaned_data['start_date']
        budget = form.cleaned_data.get('budget')

        project = Project.objects.create(
            client=client,
            title=title,
            description=description,
            start_date=start_date,
            budget=budget,
        )

        # Link back to result
        result.project = project
        result.save()

        # Create PIF from parsed data if available, otherwise seed basics
        parsed = parse_pif_excel(result.pif_file) if result.pif_file else {}
        pif = ProjectInformationForm.objects.create(project=project)
        pif.project_number = parsed.get('project_number') or (result.project_number or '')
        pif.project_name = parsed.get('project_name') or (result.project_name or '')
        pif.client_name = parsed.get('client_name') or (client.company or client.name)
        # Map remaining parsed fields
        field_names = [f.name for f in ProjectInformationForm._meta.fields if f.name not in ('id', 'project', 'project_number', 'project_name', 'client_name')]
        for key, val in parsed.items():
            if key in field_names:
                setattr(pif, key, val)
        pif.save()

        # Optionally update project budget from parsed if not supplied in form
        if budget is None and parsed.get('project_budget') is not None:
            project.budget = parsed['project_budget']
            project.save()

        messages.success(request, 'Created project from scan result and linked it.')
        return redirect('billing:project_dashboard', project_id=project.id)

    messages.error(request, 'Please correct the errors in the form.')
    return redirect('billing:pif_scan_result_detail', result_id=result.id)

@staff_member_required
@require_http_methods(["POST"])
def pif_create_client_and_project_from_result(request, result_id):
    """Create a new Client and a new Project from the scan result and link the project."""
    result = get_object_or_404(PIFScanResult, id=result_id)
    form = CreateClientAndProjectFromScanForm(request.POST)
    if form.is_valid():
        # Create the new client
        client = Client.objects.create(
            name=form.cleaned_data['client_name'],
            company=form.cleaned_data['client_company'],
            email=form.cleaned_data['client_email'],
            phone=form.cleaned_data['client_phone'],
            address=form.cleaned_data['client_address'],
            billing_contact=form.cleaned_data.get('client_billing_contact') or '',
            billing_contact_email=form.cleaned_data.get('client_billing_contact_email') or '',
        )
        
        # Create the new project
        project = Project.objects.create(
            client=client,
            title=form.cleaned_data['project_title'],
            description=form.cleaned_data.get('project_description') or '',
            start_date=form.cleaned_data['project_start_date'],
            budget=form.cleaned_data.get('project_budget'),
        )

        # Link the scan result to the new project
        result.project = project
        result.save()

        # Create PIF from parsed data if available, otherwise seed basics
        parsed = parse_pif_excel(result.pif_file) if result.pif_file else {}
        pif = ProjectInformationForm.objects.create(project=project)
        pif.project_number = parsed.get('project_number') or (result.project_number or '')
        pif.project_name = parsed.get('project_name') or (result.project_name or '')
        pif.client_name = parsed.get('client_name') or (client.company or client.name)
        # Map remaining parsed fields
        field_names = [f.name for f in ProjectInformationForm._meta.fields if f.name not in ('id', 'project', 'project_number', 'project_name', 'client_name')]
        for key, val in parsed.items():
            if key in field_names:
                setattr(pif, key, val)
        pif.save()

        # Optionally update project budget from parsed if not supplied in form
        budget = form.cleaned_data.get('project_budget')
        if budget is None and parsed.get('project_budget') is not None:
            project.budget = parsed['project_budget']
            project.save()

        messages.success(request, f'Created new client "{client.company}" and project from scan result.')
        return redirect('billing:project_dashboard', project_id=project.id)

    messages.error(request, 'Please correct the errors in the form.')
    return redirect('billing:pif_scan_result_detail', result_id=result.id)

@staff_member_required
@require_http_methods(["POST"])
def pif_update_field_mapping(request, result_id):
    """Update field mappings from the PIF scan result and apply them to the result."""
    result = get_object_or_404(PIFScanResult, id=result_id)

    # Re-parse with updated mappings
    parsed = parse_pif_excel(result.pif_file, use_second_sheet_only=True) if result.pif_file else {}

    # Collect user-confirmed mappings from form
    updated_fields = {}
    field_count = 0

    # Iterate through all field_X_mapping entries in POST data
    while f'field_{field_count}_mapping' in request.POST:
        field_name = request.POST.get(f'field_{field_count}_mapping')
        field_value = request.POST.get(f'field_{field_count}_value')
        is_accepted = f'field_{field_count}_accept' in request.POST

        if field_name and field_value and is_accepted:
            updated_fields[field_name] = field_value

        field_count += 1

    # Update the result with confirmed values
    if 'project_number' in updated_fields:
        result.project_number = updated_fields['project_number']
    if 'project_name' in updated_fields:
        result.project_name = updated_fields['project_name']
    result.save()

    # If linked to a project, update the project's PIF with confirmed mappings
    if result.project:
        pif, created = ProjectInformationForm.objects.get_or_create(project=result.project)

        # Map the confirmed fields to PIF
        for field_name, field_value in updated_fields.items():
            if hasattr(pif, field_name):
                # Handle type conversions
                if field_name in ('fee_contract_amount', 'expenses'):
                    from decimal import Decimal, InvalidOperation
                    try:
                        setattr(pif, field_name, Decimal(str(field_value).replace(',', '')))
                    except (InvalidOperation, ValueError):
                        pass
                elif field_name in ('date_entered', 'project_start_date'):
                    import pandas as pd
                    try:
                        dt = pd.to_datetime(field_value, errors='coerce')
                        if not pd.isna(dt):
                            setattr(pif, field_name, dt.date())
                    except Exception:
                        pass
                else:
                    setattr(pif, field_name, field_value)

        pif.save()

        # Update project budget if contract amount is mapped
        if 'fee_contract_amount' in updated_fields:
            try:
                from decimal import Decimal
                result.project.budget = Decimal(str(updated_fields['fee_contract_amount']).replace(',', ''))
                result.project.save()
            except Exception:
                pass

    messages.success(request, f'Updated field mappings. {len(updated_fields)} fields confirmed and saved.')
    return redirect('billing:pif_scan_result_detail', result_id=result.id)

@staff_member_required
def pif_scan_schedule_create(request):
    """Create a new PIF scan schedule"""
    if request.method == 'POST':
        form = PIFScanScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'Scan schedule "{schedule.name}" created successfully.')
            return redirect('billing:pif_scan_schedule_detail', schedule_id=schedule.id)
    else:
        form = PIFScanScheduleForm()
    
    context = {
        'form': form,
        'is_create': True,
    }
    
    return render(request, 'billing/pif_scan_schedule_form.html', context)

@staff_member_required
def pif_scan_schedule_detail(request, schedule_id):
    """View details of a PIF scan schedule"""
    schedule = get_object_or_404(PIFScanSchedule, id=schedule_id)
    
    context = {
        'schedule': schedule,
    }
    
    return render(request, 'billing/pif_scan_schedule_detail.html', context)

@staff_member_required
def toggle_pif_scan_schedule(request, schedule_id):
    """Toggle a PIF scan schedule on/off"""
    schedule = get_object_or_404(PIFScanSchedule, id=schedule_id)
    
    if request.method == 'POST':
        schedule.is_active = not schedule.is_active
        schedule.save()
        
        status = 'activated' if schedule.is_active else 'deactivated'
        messages.success(request, f'Scan schedule "{schedule.name}" {status}.')
    
    return redirect('billing:pif_scan_schedule_detail', schedule_id=schedule.id)

@staff_member_required
def import_pif_scan_csv(request):
    """Import PIF scan results from CSV file"""
    if request.method == 'POST':
        form = PIFScanCSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            batch_name = form.cleaned_data['batch_name']
            description = form.cleaned_data['description']
            update_existing = form.cleaned_data['update_existing']
            
            try:
                # Create batch
                batch = PIFScanBatch.objects.create(
                    name=batch_name,
                    description=description,
                    status='completed'
                )
                
                # Import CSV data
                import csv
                import io
                
                csv_content = csv_file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                imported_count = 0
                for row in csv_reader:
                    # Check if result already exists
                    existing = None
                    if update_existing:
                        existing = PIFScanResult.objects.filter(
                            container_dir=row.get('container_dir', ''),
                            scan_batch__name=batch_name
                        ).first()
                    
                    if existing and update_existing:
                        # Update existing
                        existing.status = row.get('status', 'skipped')
                        existing.reason = row.get('reason', '')
                        existing.pif_file = row.get('pif_file', '')
                        existing.files_count = int(row.get('files_count', 0)) if row.get('files_count') else None
                        existing.rows = int(row.get('rows', 0)) if row.get('rows') else None
                        existing.save()
                    else:
                        # Create new
                        scan_result = PIFScanResult.objects.create(
                            scan_batch=batch,
                            container_dir=row.get('container_dir', ''),
                            folder_kind=row.get('folder_kind', ''),
                            pif_file=row.get('pif_file', ''),
                            files_count=int(row.get('files_count', 0)) if row.get('files_count') else None,
                            rows=int(row.get('rows', 0)) if row.get('rows') else None,
                            status=row.get('status', 'skipped'),
                            reason=row.get('reason', ''),
                        )
                        scan_result.extract_project_info_from_path()
                        scan_result.save()
                        
                        # Try to automatically link to existing project
                        scan_result.link_to_project()
                    
                    imported_count += 1
                
                # Consolidate duplicates
                consolidated_count, deleted_count = PIFScanResult.consolidate_duplicates(batch)
                
                # Update batch statistics
                batch.total_scanned = batch.scan_results.count()
                batch.total_ingested = batch.scan_results.filter(status='ingested').count()
                batch.total_skipped = batch.scan_results.filter(status='skipped').count()
                batch.total_errors = batch.scan_results.filter(status='error').count()
                batch.completed_at = timezone.now()
                batch.save()
                
                if consolidated_count > 0:
                    messages.success(request, f'Successfully imported {imported_count} scan results. Consolidated {consolidated_count} duplicate projects, removed {deleted_count} duplicate entries.')
                else:
                    messages.success(request, f'Successfully imported {imported_count} scan results.')
                return redirect('billing:pif_scan_batch_detail', batch_id=batch.id)
                
            except Exception as e:
                messages.error(request, f'Error importing CSV: {str(e)}')
    else:
        form = PIFScanCSVImportForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'billing/pif_scan_csv_import.html', context)

@staff_member_required
def pif_project_search(request):
    """API endpoint for searching PIF scan results by project"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
    
    # Search in scan results
    scan_results = PIFScanResult.objects.filter(
        Q(project_number__icontains=query) |
        Q(project_name__icontains=query)
    ).filter(status='ingested')[:10]
    
    results = []
    for result in scan_results:
        results.append({
            'id': result.id,
            'project_number': result.project_number,
            'project_name': result.project_name,
            'pif_file': result.pif_file,
            'container_dir': result.container_dir,
        })

    return JsonResponse({'results': results})

@login_required
@require_http_methods(["GET"])
def get_project_quick_look(request, project_id):
    """
    Return quick-look billing data for a project including:
    - Phase-by-phase completion breakdown
    - Overall percent completion
    - Billing summary
    - Recent billing progress notes (5 most recent)
    """
    project = get_object_or_404(Project, id=project_id)

    # Get project phases with completion percentages
    phases = project.phases.all().values('name', 'percent_complete', 'status')

    # Calculate overall percent completion (average of phases)
    if phases:
        total_completion = sum(p['percent_complete'] for p in phases)
        overall_completion = total_completion / len(phases)
    else:
        overall_completion = 0.0

    # Get billing summary
    billing_details = project.billing_details.all()
    total_invoiced = billing_details.filter(status__in=['sent', 'paid']).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')), output_field=DecimalField())
    )['total']

    total_paid = billing_details.filter(status='paid').aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')), output_field=DecimalField())
    )['total']

    # Get contract amount from PIF or project budget
    pif = getattr(project, 'pif', None)
    contract_amount = pif.fee_contract_amount if pif and pif.fee_contract_amount else project.budget

    # Calculate outstanding
    outstanding = contract_amount - total_paid if contract_amount else Decimal('0.00')

    # Get recent billing progress notes
    from .models import BillingProgressNote
    recent_notes = BillingProgressNote.objects.filter(project=project).select_related('created_by')[:5]

    notes_data = []
    for note in recent_notes:
        notes_data.append({
            'id': note.id,
            'note_text': note.note_text,
            'created_by': note.created_by.get_full_name() if note.created_by else 'Unknown',
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M'),
        })

    data = {
        'project_id': project.id,
        'project_title': project.title,
        'overall_completion': round(overall_completion, 1),
        'phases': list(phases),
        'billing_summary': {
            'contract_amount': str(contract_amount) if contract_amount else '0.00',
            'total_invoiced': str(total_invoiced),
            'total_paid': str(total_paid),
            'outstanding': str(outstanding),
        },
        'recent_notes': notes_data,
    }

    return JsonResponse({'success': True, 'data': data})

@login_required
@require_http_methods(["POST"])
def save_billing_progress_note(request, project_id):
    """
    Save a new billing progress note for a project
    """
    project = get_object_or_404(Project, id=project_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)

    note_text = payload.get('note_text', '').strip()

    if not note_text:
        return JsonResponse({'success': False, 'error': 'Note text is required'}, status=400)

    # Create the billing progress note
    from .models import BillingProgressNote
    note = BillingProgressNote.objects.create(
        project=project,
        note_text=note_text,
        created_by=request.user
    )

    return JsonResponse({
        'success': True,
        'note': {
            'id': note.id,
            'note_text': note.note_text,
            'created_by': note.created_by.get_full_name() if note.created_by else 'Unknown',
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M'),
        }
    })

@login_required
@require_http_methods(["POST"])
def update_project_completion(request, project_id):
    """
    Update project phase completion percentages
    """
    project = get_object_or_404(Project, id=project_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

    phases_data = payload.get('phases', [])

    if not phases_data:
        return JsonResponse({'success': False, 'message': 'No phases data provided'}, status=400)

    # Update each phase
    updated_count = 0
    for phase_update in phases_data:
        phase_name = phase_update.get('name')
        percent_complete = phase_update.get('percent_complete')

        if phase_name is None or percent_complete is None:
            continue

        # Find matching phase by name
        try:
            phase = project.phases.get(name=phase_name)
            phase.percent_complete = float(percent_complete)
            phase.save()
            updated_count += 1
        except project.phases.model.DoesNotExist:
            # Phase not found, skip
            continue
        except ValueError:
            # Invalid percent_complete value
            continue

    if updated_count == 0:
        return JsonResponse({'success': False, 'message': 'No phases were updated'}, status=400)

    return JsonResponse({
        'success': True,
        'message': f'Updated {updated_count} phase(s) successfully'
    })
