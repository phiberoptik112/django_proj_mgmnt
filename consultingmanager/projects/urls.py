from django.urls import path
from . import views
from files.views import dashboard_project_details
from .views import (
    ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, ProjectDeleteView, ProjectDashboardView,
    ProjectPhaseCreateView, ProjectPhaseUpdateView,
    PhaseWorkLogCreateView, PhaseWorkLogUpdateView,
    MilestoneCreateView, MilestoneUpdateView
)

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project-list'),
    path('create/', views.ProjectCreateView.as_view(), name='project-create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project-update'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project-delete'),
    path('dashboard/', views.ProjectDashboardView.as_view(), name='project-dashboard'),
    path('dashboard/project-details/<int:project_id>/', dashboard_project_details, name='dashboard-project-details'),
    path('phase/add/<int:project_id>/', ProjectPhaseCreateView.as_view(), name='phase-add'),
    path('phase/<int:pk>/edit/', ProjectPhaseUpdateView.as_view(), name='phase-edit'),
    path('worklog/add/<int:phase_id>/', PhaseWorkLogCreateView.as_view(), name='worklog-add'),
    path('worklog/<int:pk>/edit/', PhaseWorkLogUpdateView.as_view(), name='worklog-edit'),
    path('milestone/add/<int:project_id>/', MilestoneCreateView.as_view(), name='milestone-add'),
    path('milestone/<int:pk>/edit/', MilestoneUpdateView.as_view(), name='milestone-edit'),
    path('scope/<int:pk>/', views.scope_item_detail, name='scope-detail'),
    path('scope/add/<int:project_id>/', views.scope_item_create, name='scope-add'),
] 