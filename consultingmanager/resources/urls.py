from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    # Staff management
    path('staff/', views.StaffListView.as_view(), name='staff-list'),
    path('staff/<int:pk>/', views.StaffDetailView.as_view(), name='staff-detail'),
    path('staff/create/', views.StaffCreateView.as_view(), name='staff-create'),
    path('staff/<int:pk>/update/', views.StaffUpdateView.as_view(), name='staff-update'),
    
    # Project assignments
    path('assignments/', views.AssignmentListView.as_view(), name='assignment-list'),
    path('assignments/create/', views.AssignmentCreateView.as_view(), name='assignment-create'),
    path('assignments/<int:pk>/update/', views.AssignmentUpdateView.as_view(), name='assignment-update'),
    
    # Offices
    path('offices/', views.OfficeListView.as_view(), name='office-list'),
    path('offices/<int:pk>/', views.OfficeDetailView.as_view(), name='office-detail'),
    path('offices/create/', views.OfficeCreateView.as_view(), name='office-create'),
    
    # Equipment
    path('equipment/', views.EquipmentListView.as_view(), name='equipment-list'),
    path('equipment/<int:pk>/', views.EquipmentDetailView.as_view(), name='equipment-detail'),
    path('equipment/create/', views.EquipmentCreateView.as_view(), name='equipment-create'),
    path('equipment/<int:pk>/update/', views.EquipmentUpdateView.as_view(), name='equipment-update'),
    path('equipment/<int:pk>/checkout/', views.equipment_checkout, name='equipment-checkout'),
    path('equipment/usage/<int:pk>/return/', views.equipment_return, name='equipment-return'),
    
    # Subconsultants
    path('subconsultants/', views.SubconsultantListView.as_view(), name='subconsultant-list'),
    path('subconsultants/<int:pk>/', views.SubconsultantDetailView.as_view(), name='subconsultant-detail'),
    path('subconsultants/create/', views.SubconsultantCreateView.as_view(), name='subconsultant-create'),
    path('subconsultants/<int:pk>/update/', views.SubconsultantUpdateView.as_view(), name='subconsultant-update'),
    
    # Resource dashboard
    path('', views.ResourceDashboardView.as_view(), name='dashboard'),
]
