from django.db import models

class TimelineData(models.Model):
    """Cache processed timeline data for performance"""
    project = models.OneToOneField('projects.Project', on_delete=models.CASCADE)
    events_json = models.JSONField(default=list)
    correlations_json = models.JSONField(default=list)
    last_updated = models.DateTimeField(auto_now=True)
    
    def to_unified_format(self):
        """Convert to format expected by unified_visualizer"""
        return {
            "events": self.events_json,
            "correlations": self.correlations_json,
            "metadata": {
                "generation_time": int(self.last_updated.timestamp()),
                "project_id": self.project.id,
                "project_title": self.project.title,
            }
        }