from django.urls import path
from . import views
from files.views import dashboard_project_details
from .views import (
    HomeDashboardView,
    ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, ProjectDeleteView, ProjectDashboardView,
    ProjectPhaseCreateView, ProjectPhaseUpdateView,
    PhaseWorkLogCreateView, PhaseWorkLogUpdateView,
    MilestoneCreateView, MilestoneUpdateView,
    RecItemListView, RecItemDetailView, RecItemCreateView, RecItemUpdateView, RecItemDeleteView,
    RecItemVersionListView, RecItemVersionCreateView,
    RecItemAttributeCreateView, RecItemAttributeUpdateView, RecItemAttributeDeleteView,
    RecItemDashboardView,
    ProjectTemplateListView, ProjectTemplateCreateView, ProjectTemplateUpdateView,
    ActivityLogView,
    BudgetBurnDownView,
)

app_name = 'projects'

urlpatterns = [
    path('home/', HomeDashboardView.as_view(), name='home-dashboard'),
    path('global-search/', views.global_search, name='global-search'),
    path('', views.ProjectListView.as_view(), name='project-list'),
    path('create/', views.ProjectCreateView.as_view(), name='project-create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project-update'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project-delete'),
    path('dashboard/', views.ProjectDashboardView.as_view(), name='project-dashboard'),
    path('dashboard/project-details/<int:project_id>/', dashboard_project_details, name='dashboard-project-details'),
    path('recitem-dashboard/', RecItemDashboardView.as_view(), name='recitem-dashboard'),
    path('phase/add/<int:project_id>/', ProjectPhaseCreateView.as_view(), name='phase-add'),
    path('phase/<int:pk>/edit/', ProjectPhaseUpdateView.as_view(), name='phase-edit'),
    path('worklog/add/<int:phase_id>/', PhaseWorkLogCreateView.as_view(), name='worklog-add'),
    path('worklog/<int:pk>/edit/', PhaseWorkLogUpdateView.as_view(), name='worklog-edit'),
    path('milestone/add/<int:project_id>/', MilestoneCreateView.as_view(), name='milestone-add'),
    path('milestone/<int:pk>/edit/', MilestoneUpdateView.as_view(), name='milestone-edit'),
    path('scope/<int:pk>/', views.scope_item_detail, name='scope-detail'),
    path('scope/add/<int:project_id>/', views.scope_item_create, name='scope-add'),
    
    # RecItem URLs
    path('scope/<int:scope_item_id>/recitems/', RecItemListView.as_view(), name='recitem-list'),
    path('recitem/<int:pk>/', RecItemDetailView.as_view(), name='recitem-detail'),
    path('recitem/add/<int:scope_item_id>/', RecItemCreateView.as_view(), name='recitem-add'),
    path('recitem/<int:pk>/update/', RecItemUpdateView.as_view(), name='recitem-update'),
    path('recitem/<int:pk>/delete/', RecItemDeleteView.as_view(), name='recitem-delete'),
    
    # RecItemVersion URLs
    path('recitem/<int:rec_item_id>/versions/', RecItemVersionListView.as_view(), name='recitemversion-list'),
    path('recitem/<int:rec_item_id>/version/add/', RecItemVersionCreateView.as_view(), name='recitemversion-add'),
    
    # RecItemAttribute URLs
    path('recitem/<int:rec_item_id>/attribute/add/', RecItemAttributeCreateView.as_view(), name='recitemattribute-add'),
    path('recitemattribute/<int:pk>/update/', RecItemAttributeUpdateView.as_view(), name='recitemattribute-update'),
    path('recitemattribute/<int:pk>/delete/', RecItemAttributeDeleteView.as_view(), name='recitemattribute-delete'),
    
    # RecItem Analysis URLs
    path('<int:project_id>/analyze-recitems/', views.analyze_project_recitems, name='analyze-recitems'),
    
    # Proposal Scanner URLs
    path('<int:project_id>/scan-proposal/', views.ProposalScanView.as_view(), name='proposal-scan'),
    path('proposal-scan-result/<int:pk>/', views.ProposalScanResultView.as_view(), name='proposal-scan-result'),
    path('proposal-scan-result/<int:scan_result_id>/apply-categories/', views.ApplyCategoriesView.as_view(), name='apply-categories'),
    
    # Duplicate Project
    path('<int:project_id>/duplicate/', views.duplicate_project, name='duplicate-project'),
    
    # Export
    path('export/excel/', views.export_projects_excel, name='export-excel'),
    
    # Quick Time Entry
    path('<int:project_id>/quick-time-entry/', views.quick_time_entry, name='quick-time-entry'),
    
    # Project Templates
    path('templates/', ProjectTemplateListView.as_view(), name='template-list'),
    path('templates/create/', ProjectTemplateCreateView.as_view(), name='template-create'),
    path('templates/<int:pk>/edit/', ProjectTemplateUpdateView.as_view(), name='template-update'),
    path('<int:project_id>/apply-template/<int:template_id>/', views.apply_template_to_project, name='apply-template'),
    
    # Activity Log
    path('activity-log/', ActivityLogView.as_view(), name='activity-log'),
    path('<int:project_id>/activity-log/', ActivityLogView.as_view(), name='project-activity-log'),
    
    # Budget Burn-Down
    path('<int:pk>/budget/', BudgetBurnDownView.as_view(), name='budget-burndown'),
    path('<int:project_id>/budget/api/', views.budget_burndown_api, name='budget-burndown-api'),
] 