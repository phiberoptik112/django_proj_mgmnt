from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'projects', views.ProjectTimelineViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('unified-timeline/', views.UnifiedTimelineView.as_view()),
    path('unified-timeline/<int:project_id>/', views.UnifiedTimelineView.as_view()),
]