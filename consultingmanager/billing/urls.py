from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('accounting/summary/', views.all_projects_invoicing_summary, name='invoicing_summary'),
    path('project/<int:project_id>/', views.project_billing_dashboard, name='project_dashboard'),
    path('pif/<int:project_id>/create/', views.pif_create, name='pif_create'),
    path('pif/<int:project_id>/edit/', views.pif_edit, name='pif_edit'),
    path('email/<int:email_id>/detail/', views.email_detail_modal, name='email_detail'),
    path('email/<int:email_id>/link/', views.link_email_to_billing, name='link_email'),
    # Panel API endpoints
    path('api/project/<int:project_id>/billing-instructions/', views.get_billing_instructions, name='get_billing_instructions'),
    path('api/project/<int:project_id>/billing-instructions/save/', views.save_billing_instructions, name='save_billing_instructions'),
    # Quick-look API endpoints
    path('api/project/<int:project_id>/quick-look/', views.get_project_quick_look, name='get_project_quick_look'),
    path('api/project/<int:project_id>/billing-note/', views.save_billing_progress_note, name='save_billing_note'),
    path('api/project/<int:project_id>/update-completion/', views.update_project_completion, name='update_project_completion'),
    
    # PIF Scanner URLs
    path('pif-scanner/', views.pif_scanner_dashboard, name='pif_scanner_dashboard'),
    path('pif-scanner/batch/create/', views.pif_scan_batch_create, name='pif_scan_batch_create'),
    path('pif-scanner/batch/<int:batch_id>/', views.pif_scan_batch_detail, name='pif_scan_batch_detail'),
    path('pif-scanner/batch/<int:batch_id>/run/', views.run_pif_scan_batch, name='run_pif_scan_batch'),
    path('pif-scanner/batch/<int:batch_id>/rerun/', views.pif_scan_batch_rerun, name='pif_scan_batch_rerun'),
    path('pif-scanner/batch/<int:batch_id>/delete/', views.pif_scan_batch_delete, name='pif_scan_batch_delete'),
    path('pif-scanner/batch/<int:batch_id>/results/', views.pif_scan_results, name='pif_scan_results'),
    path('pif-scanner/result/<int:result_id>/', views.pif_scan_result_detail, name='pif_scan_result_detail'),
    path('pif-scanner/result/<int:result_id>/refresh-volume/', views.pif_refresh_volume_access, name='pif_refresh_volume_access'),
    path('pif-scanner/result/<int:result_id>/link-existing/', views.pif_link_to_existing_project, name='pif_link_existing_project'),
    path('pif-scanner/result/<int:result_id>/create-project/', views.pif_create_project_from_result, name='pif_create_project_from_result'),
    path('pif-scanner/result/<int:result_id>/create-client-project/', views.pif_create_client_and_project_from_result, name='pif_create_client_and_project_from_result'),
    path('pif-scanner/result/<int:result_id>/update-mapping/', views.pif_update_field_mapping, name='pif_update_field_mapping'),
    path('pif-scanner/schedule/create/', views.pif_scan_schedule_create, name='pif_scan_schedule_create'),
    path('pif-scanner/schedule/<int:schedule_id>/', views.pif_scan_schedule_detail, name='pif_scan_schedule_detail'),
    path('pif-scanner/schedule/<int:schedule_id>/toggle/', views.toggle_pif_scan_schedule, name='toggle_pif_scan_schedule'),
    path('pif-scanner/import-csv/', views.import_pif_scan_csv, name='import_pif_scan_csv'),
    path('pif-scanner/api/project-search/', views.pif_project_search, name='pif_project_search'),
    path('pif-upload/', views.upload_single_pif, name='upload_single_pif'),

    # PIF Generator URLs
    path('pif-generate/upload/', views.pif_generate_upload, name='pif_generate_upload'),
    path('pif-generate/review/', views.pif_generate_review, name='pif_generate_review'),
    path('pif-generate/confirm/', views.pif_generate_confirm, name='pif_generate_confirm'),
]
