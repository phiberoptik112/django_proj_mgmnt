from django.core.management.base import BaseCommand
from django.conf import settings
from files.utils.file_processor import FileProcessor
from files.models import Project
import argparse
from pathlib import Path

class Command(BaseCommand):
    help = 'Process and update metadata for consulting projects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-code',
            type=str,
            help='Specific project code to process (e.g., "23-001")'
        )
        parser.add_argument(
            '--year',
            type=str,
            help='Process all projects from a specific year'
        )
        parser.add_argument(
            '--base-path',
            type=str,
            help='Base path to projects directory',
            default=getattr(settings, 'PROJECTS_BASE_PATH', None)
        )

    def handle(self, *args, **options):
        base_path = options['base_path']
        if not base_path:
            self.stderr.write(self.style.ERROR('Base path not specified. Use --base-path or set PROJECTS_BASE_PATH in settings.'))
            return

        processor = FileProcessor(base_path)
        
        if options['project_code']:
            # Process single project
            try:
                project = processor.process_project(options['project_code'])
                self.stdout.write(self.style.SUCCESS(f'Successfully processed project {project.project_code}'))
            except ValueError as e:
                self.stderr.write(self.style.ERROR(str(e)))
                
        elif options['year']:
            # Process all projects from a specific year
            year = options['year']
            year_path = Path(base_path) / year
            
            if not year_path.exists():
                self.stderr.write(self.style.ERROR(f'Year directory {year} not found'))
                return
                
            for project_dir in year_path.iterdir():
                if not project_dir.is_dir():
                    continue
                    
                project_code = project_dir.name
                if not project_code.replace('-', '').isdigit():
                    continue
                    
                try:
                    project = processor.process_project(project_code)
                    self.stdout.write(self.style.SUCCESS(f'Successfully processed project {project.project_code}'))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Error processing project {project_code}: {str(e)}'))
                    
        else:
            # Process all projects
            for year_dir in Path(base_path).iterdir():
                if not year_dir.is_dir():
                    continue
                    
                for project_dir in year_dir.iterdir():
                    if not project_dir.is_dir():
                        continue
                        
                    project_code = project_dir.name
                    if not project_code.replace('-', '').isdigit():
                        continue
                        
                    try:
                        project = processor.process_project(project_code)
                        self.stdout.write(self.style.SUCCESS(f'Successfully processed project {project.project_code}'))
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'Error processing project {project_code}: {str(e)}')) 