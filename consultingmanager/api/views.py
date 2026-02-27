from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from projects.models import Project
from clients.models import Client
from files.models import File, Proposal

from .serializers import (
    ProjectSerializer,
    FileSerializer,
    ProposalSerializer,
    ClientSerializer,
    extract_standards_from_text,
)


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:    GET /api/projects/
    retrieve: GET /api/projects/{id}/
    context:  GET /api/projects/{id}/context/
    sync:     POST /api/projects/{id}/sync/
    """
    queryset = Project.objects.select_related('client').all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return super().get_object()
        except Exception:
            raise NotFound(detail='Project not found')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'results': serializer.data, 'count': queryset.count()})

    @action(detail=True, methods=['get'])
    def context(self, request, pk=None):
        """Rich context endpoint for AI agents."""
        project = get_object_or_404(
            Project.objects.select_related('client'), pk=pk
        )

        scope = list(project.scope_items.values_list('description', flat=True))
        standards = extract_standards_from_text(' '.join(scope))
        recent_files_qs = project.files.order_by('-uploaded_at')[:10]
        proposals_qs = project.proposals.all()

        return Response({
            'project': ProjectSerializer(project).data,
            'scope': scope,
            'standards': standards,
            'recent_files': FileSerializer(recent_files_qs, many=True).data,
            'proposals': ProposalSerializer(proposals_qs, many=True).data,
            'metadata': {
                'client_technical_level': 'moderate',
                'priority': 'medium',
                'notes': project.description or '',
            },
        })

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Cache invalidation placeholder."""
        project = get_object_or_404(Project, pk=pk)
        return Response({'status': 'synced', 'project_id': project.id})


class FileListView(APIView):
    """
    GET /api/files/
    GET /api/files/?project={project_id}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = File.objects.select_related('project').all()
        project_id = request.query_params.get('project')
        if project_id is not None:
            qs = qs.filter(project_id=project_id)
        serializer = FileSerializer(qs, many=True)
        return Response({'results': serializer.data, 'count': qs.count()})


class ProjectFileUploadView(APIView):
    """
    POST /api/projects/{pk}/files/upload/
    Content-Type: multipart/form-data
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response(
                {'detail': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_instance = File.objects.create(
            project=project,
            title=file_obj.name,
            file=file_obj,
            file_type='document',
            description=request.data.get('description', 'Uploaded via API'),
        )

        return Response(
            {
                'id': file_instance.id,
                'url': file_instance.file.url,
                'message': 'File uploaded successfully',
            },
            status=status.HTTP_201_CREATED,
        )


class ProposalListView(APIView):
    """
    GET /api/proposals/
    GET /api/proposals/?project={project_id}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Proposal.objects.all()
        project_id = request.query_params.get('project')
        if project_id is not None:
            qs = qs.filter(project_id=project_id)
        serializer = ProposalSerializer(qs, many=True)
        return Response({'results': serializer.data, 'count': qs.count()})


class ClientDetailView(APIView):
    """
    GET /api/clients/{pk}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        serializer = ClientSerializer(client)
        return Response(serializer.data)
