from django.core.management.base import BaseCommand
from files.models import Project
from files.utils.project_analyzer import ProjectAnalyzer

class Command(BaseCommand):
    help = 'Run content analysis on consulting projects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-code',
            type=str,
            help='Specific project code to analyze (e.g., "23-001")'
        )
        parser.add_argument(
            '--year',
            type=str,
            help='Analyze all projects from a specific year'
        )
        parser.add_argument(
            '--analysis-type',
            type=str,
            choices=['all', 'proposal', 'scope'],
            default='all',
            help='Type of analysis to perform'
        )

    def handle(self, *args, **options):
        project_code = options['project_code']
        year = options['year']
        analysis_type = options['analysis_type']
        
        # Get projects to analyze
        projects = Project.objects.all()
        if project_code:
            projects = projects.filter(project_code=project_code)
        elif year:
            projects = projects.filter(year=year)
            
        if not projects.exists():
            self.stderr.write(self.style.ERROR('No projects found matching the criteria'))
            return
            
        # Analyze each project
        for project in projects:
            try:
                analyzer = ProjectAnalyzer(project)
                analyzer.analyze_project()
                self.stdout.write(self.style.SUCCESS(f'Successfully analyzed project {project.project_code}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error analyzing project {project.project_code}: {str(e)}')) 