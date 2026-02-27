from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProjectViewSet,
    FileListView,
    ProjectFileUploadView,
    ProposalListView,
    ClientDetailView,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
    path('files/', FileListView.as_view(), name='file-list'),
    path('projects/<int:pk>/files/upload/', ProjectFileUploadView.as_view(), name='project-file-upload'),
    path('proposals/', ProposalListView.as_view(), name='proposal-list'),
    path('clients/<int:pk>/', ClientDetailView.as_view(), name='client-detail'),
]
