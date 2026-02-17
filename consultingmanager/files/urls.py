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
    
    # Email Timeline Scanner URLs
    path('email-scanner/', views.email_scanner_dashboard, name='email-scanner-dashboard'),
    path('email-scanner/batch/create/', views.email_scan_batch_create, name='email-scan-batch-create'),
    path('email-scanner/batch/<int:batch_id>/', views.email_scan_batch_detail, name='email-scan-batch-detail'),
    path('email-scanner/batch/<int:batch_id>/run/', views.run_email_scan_batch, name='run-email-scan-batch'),
    path('email-scanner/batch/<int:batch_id>/delete/', views.email_scan_batch_delete, name='email-scan-batch-delete'),
    path('email-scanner/review/', views.email_event_review, name='email-event-review'),
    path('email-scanner/review/<int:batch_id>/', views.email_event_review, name='email-event-review-batch'),
    path('email-scanner/event/<int:event_id>/', views.email_event_detail, name='email-event-detail'),
    path('email-scanner/event/<int:event_id>/confirm/', views.confirm_email_event, name='confirm-email-event'),
    path('email-scanner/event/<int:event_id>/reject/', views.reject_email_event, name='reject-email-event'),
    path('email-scanner/event/<int:event_id>/convert/', views.convert_event_to_milestone, name='convert-event-to-milestone'),
    path('email-scanner/bulk-action/', views.bulk_event_action, name='bulk-event-action'),
    path('project/<int:project_id>/email-timeline/', views.project_email_timeline, name='project-email-timeline'),
    path('project/<int:project_id>/quick-scan/', views.quick_project_scan, name='quick-project-scan'),
] 