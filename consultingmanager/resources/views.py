from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Sum, Q
from .models import (
    Office, StaffMember, ProjectAssignment,
    Equipment, EquipmentUsage,
    Subconsultant, SubconsultantContract
)


class ResourceDashboardView(LoginRequiredMixin, TemplateView):
    """Resource management dashboard"""
    template_name = 'resources/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Staff summary
        context['total_staff'] = StaffMember.objects.filter(employment_status__in=['full_time', 'part_time']).count()
        context['staff_by_role'] = StaffMember.objects.filter(
            employment_status__in=['full_time', 'part_time']
        ).values('role').annotate(count=Count('id'))
        
        # Office summary
        context['offices'] = Office.objects.filter(is_active=True)
        
        # Equipment summary
        context['total_equipment'] = Equipment.objects.exclude(status='retired').count()
        context['equipment_needing_calibration'] = Equipment.objects.filter(
            calibration_due_date__lte=timezone.now().date()
        ).count()
        context['equipment_in_use'] = Equipment.objects.filter(status='in_use').count()
        
        # Subconsultants
        context['active_subconsultants'] = Subconsultant.objects.filter(is_active=True).count()
        context['active_contracts'] = SubconsultantContract.objects.filter(status='active').count()
        
        return context


# Staff Views
class StaffListView(LoginRequiredMixin, ListView):
    model = StaffMember
    template_name = 'resources/staff_list.html'
    context_object_name = 'staff_members'
    
    def get_queryset(self):
        queryset = StaffMember.objects.select_related('user', 'office')
        
        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by office
        office = self.request.GET.get('office')
        if office:
            queryset = queryset.filter(office_id=office)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(employment_status=status)
        else:
            # Default: exclude inactive
            queryset = queryset.exclude(employment_status='inactive')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['offices'] = Office.objects.filter(is_active=True)
        context['roles'] = StaffMember.ROLE_CHOICES
        context['statuses'] = StaffMember.EMPLOYMENT_STATUS
        return context


class StaffDetailView(LoginRequiredMixin, DetailView):
    model = StaffMember
    template_name = 'resources/staff_detail.html'
    context_object_name = 'staff'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_assignments'] = self.object.assignments.filter(is_active=True).select_related('project')
        context['equipment_checkouts'] = self.object.equipment_checkouts.filter(
            return_date__isnull=True
        ).select_related('equipment')
        return context


class StaffCreateView(LoginRequiredMixin, CreateView):
    model = StaffMember
    template_name = 'resources/staff_form.html'
    fields = ['user', 'employee_id', 'office', 'role', 'title', 'employment_status',
              'standard_hourly_rate', 'internal_cost_rate', 'weekly_capacity_hours',
              'skills', 'certifications', 'phone_extension', 'mobile_phone', 'hire_date']
    success_url = reverse_lazy('resources:staff-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Staff member created successfully.')
        return super().form_valid(form)


class StaffUpdateView(LoginRequiredMixin, UpdateView):
    model = StaffMember
    template_name = 'resources/staff_form.html'
    fields = ['employee_id', 'office', 'role', 'title', 'employment_status',
              'standard_hourly_rate', 'internal_cost_rate', 'weekly_capacity_hours',
              'skills', 'certifications', 'phone_extension', 'mobile_phone', 
              'hire_date', 'termination_date']
    
    def get_success_url(self):
        return reverse_lazy('resources:staff-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Staff member updated successfully.')
        return super().form_valid(form)


# Assignment Views
class AssignmentListView(LoginRequiredMixin, ListView):
    model = ProjectAssignment
    template_name = 'resources/assignment_list.html'
    context_object_name = 'assignments'
    
    def get_queryset(self):
        return ProjectAssignment.objects.select_related(
            'project', 'staff_member', 'staff_member__user'
        ).filter(is_active=True)


class AssignmentCreateView(LoginRequiredMixin, CreateView):
    model = ProjectAssignment
    template_name = 'resources/assignment_form.html'
    fields = ['project', 'staff_member', 'role', 'allocation_percent', 
              'start_date', 'end_date', 'hourly_rate_override', 'notes']
    success_url = reverse_lazy('resources:assignment-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Assignment created successfully.')
        return super().form_valid(form)


class AssignmentUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectAssignment
    template_name = 'resources/assignment_form.html'
    fields = ['role', 'allocation_percent', 'start_date', 'end_date', 
              'hourly_rate_override', 'notes', 'is_active']
    success_url = reverse_lazy('resources:assignment-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Assignment updated successfully.')
        return super().form_valid(form)


# Office Views
class OfficeListView(LoginRequiredMixin, ListView):
    model = Office
    template_name = 'resources/office_list.html'
    context_object_name = 'offices'
    
    def get_queryset(self):
        return Office.objects.annotate(
            staff_count=Count('staff', filter=Q(staff__employment_status__in=['full_time', 'part_time'])),
            equipment_count=Count('equipment', filter=~Q(equipment__status='retired'))
        )


class OfficeDetailView(LoginRequiredMixin, DetailView):
    model = Office
    template_name = 'resources/office_detail.html'
    context_object_name = 'office'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff'] = self.object.staff.filter(employment_status__in=['full_time', 'part_time'])
        context['equipment'] = self.object.equipment.exclude(status='retired')
        return context


class OfficeCreateView(LoginRequiredMixin, CreateView):
    model = Office
    template_name = 'resources/office_form.html'
    fields = ['name', 'code', 'address', 'city', 'state', 'phone', 'email', 'is_active']
    success_url = reverse_lazy('resources:office-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Office created successfully.')
        return super().form_valid(form)


# Equipment Views
class EquipmentListView(LoginRequiredMixin, ListView):
    model = Equipment
    template_name = 'resources/equipment_list.html'
    context_object_name = 'equipment_list'
    
    def get_queryset(self):
        queryset = Equipment.objects.select_related('office')
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        else:
            queryset = queryset.exclude(status='retired')
        
        # Filter by office
        office = self.request.GET.get('office')
        if office:
            queryset = queryset.filter(office_id=office)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Equipment.EQUIPMENT_CATEGORIES
        context['statuses'] = Equipment.STATUS_CHOICES
        context['offices'] = Office.objects.filter(is_active=True)
        return context


class EquipmentDetailView(LoginRequiredMixin, DetailView):
    model = Equipment
    template_name = 'resources/equipment_detail.html'
    context_object_name = 'equipment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usage_history'] = self.object.usage_records.select_related(
            'project', 'checked_out_by'
        ).order_by('-checkout_date')[:20]
        return context


class EquipmentCreateView(LoginRequiredMixin, CreateView):
    model = Equipment
    template_name = 'resources/equipment_form.html'
    fields = ['name', 'category', 'manufacturer', 'model_number', 'serial_number',
              'asset_tag', 'office', 'status', 'last_calibration_date', 
              'calibration_due_date', 'calibration_interval_days',
              'purchase_date', 'purchase_price', 'replacement_value', 'notes']
    success_url = reverse_lazy('resources:equipment-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Equipment created successfully.')
        return super().form_valid(form)


class EquipmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipment
    template_name = 'resources/equipment_form.html'
    fields = ['name', 'category', 'manufacturer', 'model_number', 'serial_number',
              'asset_tag', 'office', 'status', 'last_calibration_date', 
              'calibration_due_date', 'calibration_interval_days',
              'purchase_date', 'purchase_price', 'replacement_value', 'notes']
    
    def get_success_url(self):
        return reverse_lazy('resources:equipment-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Equipment updated successfully.')
        return super().form_valid(form)


@login_required
def equipment_checkout(request, pk):
    """Checkout equipment for a project"""
    equipment = get_object_or_404(Equipment, pk=pk)
    
    if request.method == 'POST':
        from projects.models import Project
        
        project_id = request.POST.get('project_id')
        purpose = request.POST.get('purpose', '')
        
        if not project_id:
            messages.error(request, 'Please select a project.')
            return redirect('resources:equipment-detail', pk=pk)
        
        project = get_object_or_404(Project, pk=project_id)
        
        # Get staff member for current user
        try:
            staff = request.user.staff_profile
        except StaffMember.DoesNotExist:
            messages.error(request, 'You must have a staff profile to checkout equipment.')
            return redirect('resources:equipment-detail', pk=pk)
        
        # Create usage record
        EquipmentUsage.objects.create(
            equipment=equipment,
            project=project,
            checked_out_by=staff,
            checkout_date=timezone.now(),
            purpose=purpose
        )
        
        # Update equipment status
        equipment.status = 'in_use'
        equipment.save()
        
        messages.success(request, f'Equipment checked out for {project.title}.')
        return redirect('resources:equipment-detail', pk=pk)
    
    # GET - show checkout form
    from projects.models import Project
    projects = Project.objects.filter(status__in=['planning', 'in_progress'])
    return render(request, 'resources/equipment_checkout.html', {
        'equipment': equipment,
        'projects': projects
    })


@login_required
def equipment_return(request, pk):
    """Return checked out equipment"""
    usage = get_object_or_404(EquipmentUsage, pk=pk)
    
    if request.method == 'POST':
        usage.return_date = timezone.now()
        usage.notes = request.POST.get('notes', '')
        usage.save()
        
        # Update equipment status
        usage.equipment.status = 'available'
        usage.equipment.save()
        
        messages.success(request, 'Equipment returned successfully.')
        return redirect('resources:equipment-detail', pk=usage.equipment.pk)
    
    return render(request, 'resources/equipment_return.html', {'usage': usage})


# Subconsultant Views
class SubconsultantListView(LoginRequiredMixin, ListView):
    model = Subconsultant
    template_name = 'resources/subconsultant_list.html'
    context_object_name = 'subconsultants'
    
    def get_queryset(self):
        queryset = Subconsultant.objects.all()
        
        # Filter
        if self.request.GET.get('active_only') == '1':
            queryset = queryset.filter(is_active=True)
        
        if self.request.GET.get('preferred') == '1':
            queryset = queryset.filter(is_preferred=True)
        
        return queryset


class SubconsultantDetailView(LoginRequiredMixin, DetailView):
    model = Subconsultant
    template_name = 'resources/subconsultant_detail.html'
    context_object_name = 'subconsultant'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contracts'] = self.object.contracts.select_related('project').order_by('-start_date')
        return context


class SubconsultantCreateView(LoginRequiredMixin, CreateView):
    model = Subconsultant
    template_name = 'resources/subconsultant_form.html'
    fields = ['company_name', 'contact_name', 'contact_email', 'contact_phone',
              'address', 'specialty', 'services', 'w9_on_file', 'insurance_on_file',
              'insurance_expiration', 'standard_hourly_rate', 'is_active', 'is_preferred', 'notes']
    success_url = reverse_lazy('resources:subconsultant-list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Subconsultant created successfully.')
        return super().form_valid(form)


class SubconsultantUpdateView(LoginRequiredMixin, UpdateView):
    model = Subconsultant
    template_name = 'resources/subconsultant_form.html'
    fields = ['company_name', 'contact_name', 'contact_email', 'contact_phone',
              'address', 'specialty', 'services', 'w9_on_file', 'insurance_on_file',
              'insurance_expiration', 'standard_hourly_rate', 'is_active', 'is_preferred', 'notes']
    
    def get_success_url(self):
        return reverse_lazy('resources:subconsultant-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Subconsultant updated successfully.')
        return super().form_valid(form)
