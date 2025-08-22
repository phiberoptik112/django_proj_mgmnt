from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('', views.FileListView.as_view(), name='file-list'),
    path('create/', views.FileCreateView.as_view(), name='file-create'),
    path('<int:pk>/update/', views.FileUpdateView.as_view(), name='file-update'),
    path('<int:pk>/delete/', views.FileDeleteView.as_view(), name='file-delete'),
    path('<int:pk>/', views.FileDetailView.as_view(), name='file-detail'),
    path('room-acoustics/create/<int:project_id>/', views.RoomAcousticsCreateView.room_acoustics_create, name='room-acoustics-create'),
    # Project Metadata URLs
    path('metadata/create/', views.ProjectMetadataCreateView.as_view(), name='metadata-create'),
    path('metadata/<int:pk>/', views.metadata_detail, name='metadata-detail'),
    path('metadata/<int:pk>/update/', views.ProjectMetadataUpdateView.as_view(), name='metadata-update'),
    path('metadata/<int:pk>/analyze/', views.analyze_metadata, name='metadata-analyze'),
    ### Proposal URLs
    path('proposal/create/', views.ProposalCreateView.as_view(), name='proposal-create'),
    path('proposal/<int:pk>/', views.ProposalDetailView.as_view(), name='proposal-detail'),
    path('proposal/<int:pk>/update/', views.ProposalUpdateView.as_view(), name='proposal-update'),
    path('proposal/<int:pk>/delete/', views.ProposalDeleteView.as_view(), name='proposal-delete'),
    ### End Proposal URLs
    path('proposals/import/<int:project_id>/', views.ProposalImportView.as_view(), name='proposal-import'),
    # PDF Processing
    path('process-pdfs/<int:project_id>/', views.BulkPdfProcessView.as_view(), name='process-pdfs'),
] 