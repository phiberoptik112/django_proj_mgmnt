from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from projects.models import Project
from .serializers import ProjectTimelineSerializer

class ProjectTimelineViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectTimelineSerializer
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get timeline data for specific project"""
        project = self.get_object()
        serializer = self.get_serializer(project)
        return Response(serializer.data['timeline_data'])

class UnifiedTimelineView(APIView):
    """Main endpoint that unified_visualizer will call"""
    
    def get(self, request, project_id=None):
        if project_id:
            # Single project timeline
            project = Project.objects.get(id=project_id)
            serializer = ProjectTimelineSerializer(project)
            return Response(serializer.data['timeline_data'])
        else:
            # All projects combined (your current use case)
            projects = Project.objects.all()
            all_events = []
            all_correlations = []
            
            for project in projects:
                serializer = ProjectTimelineSerializer(project)
                timeline = serializer.data['timeline_data']
                all_events.extend(timeline['events'])
                all_correlations.extend(timeline['correlations'])
            
            return Response({
                "events": all_events,
                "correlations": all_correlations,
                "metadata": {
                    "generation_time": int(timezone.now().timestamp()),
                    "total_projects": projects.count()
                }
            })