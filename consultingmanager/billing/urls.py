from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('project/<int:project_id>/', views.project_billing_dashboard, name='project_dashboard'),
    path('pif/<int:project_id>/create/', views.pif_create, name='pif_create'),
    path('pif/<int:project_id>/edit/', views.pif_edit, name='pif_edit'),
    path('email/<int:email_id>/detail/', views.email_detail_modal, name='email_detail'),
    path('email/<int:email_id>/link/', views.link_email_to_billing, name='link_email'),
]
