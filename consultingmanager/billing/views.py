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

from projects.models import Project, TimeEntry
from clients.models import Client
from files.models import Email, Proposal, FileMetadata
from .models import BillingDetail, ProjectInformationForm, BillingPhase, BillingEmailReference
from .forms import ProjectInformationFormForm, BillingPhaseFormSet

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
        }
    }

    return render(request, 'billing/invoicing_summary.html', context)

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
