from rest_framework import serializers
from projects.models import Project

class TimelineTransformer:
    """Transform Django project data to unified_visualizer format"""
    
    def __init__(self, project):
        self.project = project
    
    def generate_events(self):
        """Generate timeline events from project data"""
        events = []
        
        # File scan events from project metadata
        events.extend(self._create_file_scan_events())
        
        # Milestone events from project timeline
        events.extend(self._create_milestone_events())
        
        return events
    
    def _create_file_scan_events(self):
        """Convert project files to file scan events"""
        if not hasattr(self.project, 'metadata') or not self.project.metadata.exists():
            return []
            
        metadata = self.project.metadata.first()
        return [{
            "event_id": f"file_scan_{self.project.id}",
            "event_type": "file_scan", 
            "timestamp": int(metadata.last_analyzed.timestamp()),
            "metadata": {
                "file_count": self.project.files.count(),
                "tree_structure": self._build_file_tree()
            }
        }]
    
    def _create_milestone_events(self):
        """Convert project milestones to timeline events"""
        milestones = []
        
        # Project start milestone
        milestones.append({
            "event_id": f"milestone_start_{self.project.id}",
            "event_type": "milestone",
            "timestamp": int(self.project.start_date.timestamp()),
            "metadata": {
                "title": f"Start: {self.project.title}",
                "category": "project_start",
                "priority": "high",
                "confidence": 1.0,
                "intended_color": "#3B82F6",
                "actual_color": "#10B981"
            }
        })
        
        return milestones
    
    def _build_file_tree(self):
        """Build file tree structure for sunburst visualization"""
        return {
            "name": self.project.title,
            "type": "folder",
            "children": [
                {
                    "name": f.title,
                    "type": "file", 
                    "size": getattr(f.file_file, 'size', 1000),
                    "mime_type": self._guess_mime_type(f.title)
                }
                for f in self.project.files.all()
            ]
        }

class ProjectTimelineSerializer(serializers.ModelSerializer):
    timeline_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'title', 'timeline_data']
    
    def get_timeline_data(self, obj):
        transformer = TimelineTransformer(obj)
        events = transformer.generate_events()
        
        return {
            "events": events,
            "correlations": self._generate_correlations(events),
            "metadata": {
                "project_id": obj.id,
                "generation_time": int(timezone.now().timestamp())
            }
        }