from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('', views.FileListView.as_view(), name='file-list'),
    path('create/', views.FileCreateView.as_view(), name='file-create'),
    path('<int:pk>/update/', views.FileUpdateView.as_view(), name='file-update'),
    path('<int:pk>/delete/', views.FileDeleteView.as_view(), name='file-delete'),
] 